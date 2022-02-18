from django.http import QueryDict
from django.test import TestCase

from nautobot.core.settings_funcs import is_truthy
from nautobot.utilities.utils import (
    deepmerge,
    dict_to_filter_params,
    get_filterform_for_model,
    get_filterset_for_model,
    get_route_for_model,
    get_table_for_model,
    normalize_querydict,
)
from nautobot.dcim.models import Device, Site
from nautobot.dcim.filters import DeviceFilterSet, SiteFilterSet
from nautobot.dcim.forms import DeviceFilterForm, SiteFilterForm
from nautobot.dcim.tables import DeviceTable, SiteTable

from example_plugin.models import ExampleModel


class DictToFilterParamsTest(TestCase):
    """
    Validate the operation of dict_to_filter_params().
    """

    def test_dict_to_filter_params(self):

        input = {
            "a": True,
            "foo": {
                "bar": 123,
                "baz": 456,
            },
            "x": {"y": {"z": False}},
        }

        output = {
            "a": True,
            "foo__bar": 123,
            "foo__baz": 456,
            "x__y__z": False,
        }

        self.assertEqual(dict_to_filter_params(input), output)

        input["x"]["y"]["z"] = True

        self.assertNotEqual(dict_to_filter_params(input), output)


class NormalizeQueryDictTest(TestCase):
    """
    Validate normalize_querydict() utility function.
    """

    def test_normalize_querydict(self):
        self.assertDictEqual(
            normalize_querydict(QueryDict("foo=1&bar=2&bar=3&baz=")),
            {"foo": "1", "bar": ["2", "3"], "baz": ""},
        )


class DeepMergeTest(TestCase):
    """
    Validate the behavior of the deepmerge() utility.
    """

    def test_deepmerge(self):

        dict1 = {
            "active": True,
            "foo": 123,
            "fruits": {
                "orange": 1,
                "apple": 2,
                "pear": 3,
            },
            "vegetables": None,
            "dairy": {
                "milk": 1,
                "cheese": 2,
            },
            "deepnesting": {
                "foo": {
                    "a": 10,
                    "b": 20,
                    "c": 30,
                },
            },
        }

        dict2 = {
            "active": False,
            "bar": 456,
            "fruits": {
                "banana": 4,
                "grape": 5,
            },
            "vegetables": {
                "celery": 1,
                "carrots": 2,
                "corn": 3,
            },
            "dairy": None,
            "deepnesting": {
                "foo": {
                    "a": 100,
                    "d": 40,
                },
            },
        }

        merged = {
            "active": False,
            "foo": 123,
            "bar": 456,
            "fruits": {
                "orange": 1,
                "apple": 2,
                "pear": 3,
                "banana": 4,
                "grape": 5,
            },
            "vegetables": {
                "celery": 1,
                "carrots": 2,
                "corn": 3,
            },
            "dairy": None,
            "deepnesting": {
                "foo": {
                    "a": 100,
                    "b": 20,
                    "c": 30,
                    "d": 40,
                },
            },
        }

        self.assertEqual(deepmerge(dict1, dict2), merged)


class GetFooForModelTest(TestCase):
    """Tests for the various `get_foo_for_model()` functions."""

    def test_get_filterset_for_model(self):
        self.assertEqual(get_filterset_for_model(Device), DeviceFilterSet)
        self.assertEqual(get_filterset_for_model(Site), SiteFilterSet)

    def test_get_filterform_for_model(self):
        self.assertEqual(get_filterform_for_model(Device), DeviceFilterForm)
        self.assertEqual(get_filterform_for_model(Site), SiteFilterForm)

    def test_get_route_for_model(self):
        self.assertEqual(get_route_for_model(Device, "list"), "dcim:device_list")
        self.assertEqual(get_route_for_model(Site, "list"), "dcim:site_list")
        self.assertEqual(get_route_for_model(ExampleModel, "list"), "plugins:example_plugin:examplemodel_list")

    def test_get_table_for_model(self):
        self.assertEqual(get_table_for_model(Device), DeviceTable)
        self.assertEqual(get_table_for_model(Site), SiteTable)


class IsTruthyTest(TestCase):
    def test_is_truthy(self):
        self.assertTrue(is_truthy("true"))
        self.assertTrue(is_truthy("True"))
        self.assertTrue(is_truthy(True))
        self.assertTrue(is_truthy("yes"))
        self.assertTrue(is_truthy("on"))
        self.assertTrue(is_truthy("y"))
        self.assertTrue(is_truthy("1"))
        self.assertTrue(is_truthy(1))

        self.assertFalse(is_truthy("false"))
        self.assertFalse(is_truthy("False"))
        self.assertFalse(is_truthy(False))
        self.assertFalse(is_truthy("no"))
        self.assertFalse(is_truthy("n"))
        self.assertFalse(is_truthy(0))
        self.assertFalse(is_truthy("0"))
