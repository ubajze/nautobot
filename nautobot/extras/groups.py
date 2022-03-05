from collections import OrderedDict
import logging
import urllib

from django import forms
from django.urls import reverse
from django.utils.functional import classproperty

from nautobot.utilities.utils import get_filterset_for_model, get_form_for_model, get_route_for_model


logger = logging.getLogger(__name__)


def dynamicgroup_map_factory(model):
    """Generate a `FooDynamicGroupMap` class for a given `model`."""

    filterset_class = get_filterset_for_model(model)
    filterform_class = get_form_for_model(model, form_prefix="Filter")
    form_class = get_form_for_model(model)

    group_map = type(
        str("%sDynamicGroupMap" % model._meta.object_name),
        (BaseDynamicGroupMap,),
        {
            "model": model,
            "filterset_class": filterset_class,
            "filterform_class": filterform_class,
            "form_class": form_class,
        },
    )

    return group_map


class BaseDynamicGroupMap:
    """
    Dynamic Group mapping used to generate mappings for each model class.

    This class itself should not be invoked directly as the class variables will
    not be populated and most class methods will fail.
    """

    model = None
    form_class = None
    filterset_class = None
    filterform = None

    # This is used as a `startswith` check on field names, so these can be
    # explicit fields or just substrings. Type: tuple
    exclude_filter_fields = ("q", "cr", "cf", "comments")  # Must be a tuple

    @classproperty
    def base_url(cls):
        if cls.model is None:
            return
        route_name = get_route_for_model(cls.model, "list")
        return reverse(route_name)

    @classmethod
    def fields(cls):
        """Return all FilterForm fields in a dictionary."""
        _fields = OrderedDict()

        # Get model form and fields
        modelform = cls.form_class()
        modelform_fields = modelform.fields

        # Get filter form and fields
        filterform = cls.filterform_class()
        filter_fields = filterform.fields

        # Get filterset and fields
        filterset = cls.filterset_class()
        filterset_fields = filterset.filters

        # Model form fields that aren't on the filter form
        missing_fields = set(modelform_fields).difference(filter_fields)

        # Try a few ways to see if a missing field can be added to the filter fields.
        for missing_field in missing_fields:
            # Skip excluded fields
            if missing_field.startswith(cls.exclude_filter_fields):
                logger.debug("Skipping excluded filter field: %s", missing_field)
                continue

            # Try to fuzz fields that should be in the filter form. Sorted from
            # most to least common, so the loop break happens sooner than later.
            # FIXME(jathan): YES THIS IS GHETTO, but I'm just trying to get
            # something working that is backwards-compatible.
            # FIXME(jathan); There is a bug with `asset_tag` -> `tag`. Will need
            # to retrhink this fuzzing approach and/or replace it with a static
            # mapping or something. "Dynamic" groups indeed.
            #
            # >>> Missing: asset_tag, Guess: tag found in filter fields
            # >>> Missing: tags, Guess: tag found in filter fields
            guesses = [
                missing_field,  # foo
                missing_field + "_id",  # foo_id
                missing_field.rstrip("s"),  # tags -> tag
                "has_" + missing_field[:-1],  # primary_ip4 -> has_primary_ip
                missing_field.split("_")[-1],  # device_role -> role
            ]
            for guess in guesses:
                if guess in filter_fields:
                    logger.debug("Missing: %s, Guess: %s found in filter fields", missing_field, guess)
                    break

            # If none of the missing ones are found in some other form, add the
            # missing field.
            else:
                modelform_field = modelform_fields[missing_field]
                try:
                    filterset_field = filterset_fields[missing_field]
                except KeyError:
                    logger.debug("Skipping %s: doesn't have a filterset field", missing_field)
                    continue

                # Get ready to replace the form field w/ correct widget.
                new_modelform_field = filterset_field.field
                new_modelform_field.widget = modelform_field.widget

                # Replace the modelform_field with the correct type for the UI.
                if isinstance(modelform_field, forms.CharField):
                    modelform_field = new_modelform_field

                # Carry over the `to_field_name` to the modelform_field.
                to_field_name = filterset_field.extra.get("to_field_name")
                if to_field_name is not None:
                    modelform_field.to_field_name = to_field_name

                logger.debug("Added %s (%s) to filter fields", missing_field, modelform_field.__class__.__name__)
                filter_fields[missing_field] = modelform_field

        for field_name, filter_field in filter_fields.items():
            # Skip excluded fields
            if field_name.startswith(cls.exclude_filter_fields):
                logger.debug("Skipping excluded filter field: %s", field_name)
                continue

            _fields[field_name] = filter_field

        return _fields

    @classmethod
    def get_queryset(cls, filter_params, flat=False):
        """
        Return a queryset matching the dynamic group `filter_params`.

        The queryset is generated based of the FilterSet for this map.
        """
        filterset = cls.filterset_class(filter_params, cls.model.objects.all())

        if flat:
            return filterset.qs.values_list("pk", flat=True)
        return filterset.qs

    @classmethod
    def urlencode(cls, filter_params):
        """
        Given a `filter_params` dict, return a URL-encoded HTTP query string.

        For example:
            >>> dg = DynamicGroup.objects.first()
            >>> filter_params = {"site": ["ams01", "bkk01"], "has_primary_ip": True}
            >>> dg.map.urlencode(filter_params)
            site=ams01&site=bkk01&has_primary_ip=True'

        """
        return urllib.parse.urlencode(filter_params, doseq=True)
