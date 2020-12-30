from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from dcim.models import Site, Rack
from ipam.models import VLAN
from extras.choices import *
from extras.models import Relationship, RelationshipAssociation
from utilities.testing import TestCase
from utilities.forms import DynamicModelChoiceField, DynamicModelMultipleChoiceField


class RelationshipBaseTest(TestCase):

    def setUp(self):

        self.site_ct = ContentType.objects.get_for_model(Site)
        self.rack_ct = ContentType.objects.get_for_model(Rack)
        self.vlan_ct = ContentType.objects.get_for_model(VLAN)

        self.m2m_1 = Relationship(
            name="Vlan to Rack",
            slug="vlan-rack",
            source_type=self.rack_ct,
            source_label="My Vlans",
            source_filter={"site": "mysite"},
            destination_type=self.vlan_ct,
            destination_label="My Racks",
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY
        )
        self.m2m_1.save()

        self.m2m_2 = Relationship(
            name="Another Vlan to Rack",
            slug="vlan-rack-2",
            source_type=self.rack_ct,
            destination_type=self.vlan_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY
        )
        self.m2m_2.save()

        self.o2m_1 = Relationship(
            name="generic site to vlan",
            slug="site-vlan",
            source_type=self.site_ct,
            destination_type=self.vlan_ct,
            type=RelationshipTypeChoices.TYPE_ONE_TO_MANY
        )
        self.o2m_1.save()

        self.o2o_1 = Relationship(
            name="Primary Rack per Site",
            slug="primary-rack-site",
            source_type=self.rack_ct,
            source_hidden=True,
            destination_type=self.site_ct,
            destination_label="Primary Rack",
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE
        )
        self.o2o_1.save()

        self.sites = [
            Site(name='Site A', slug='site-a'),
            Site(name='Site B', slug='site-b'),
            Site(name='Site C', slug='site-c'),
        ]
        Site.objects.bulk_create(self.sites)

        self.racks = [
            Rack(name='Rack A', site=self.sites[0]),
            Rack(name='Rack B', site=self.sites[1]),
            Rack(name='Rack C', site=self.sites[2]),
        ]
        Rack.objects.bulk_create(self.racks)

        self.vlans = [
            VLAN(name='VLAN A', vid=100, site=self.sites[0]),
            VLAN(name='VLAN B', vid=100, site=self.sites[1]),
            VLAN(name='VLAN C', vid=100, site=self.sites[2]),
        ]
        VLAN.objects.bulk_create(self.vlans)


class RelationshipTest(RelationshipBaseTest):

    def test_clean_filter_not_dict(self):
        m2m = Relationship(
            name="Another Vlan to Rack",
            slug="vlan-rack-2",
            source_type=self.site_ct,
            source_filter=["a list not a dict"],
            destination_type=self.rack_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY
        )

        with self.assertRaises(ValidationError):
            m2m.clean()

    def test_clean_filter_not_valid(self):
        m2m = Relationship(
            name="Another Vlan to Rack",
            slug="vlan-rack-2",
            source_type=self.site_ct,
            source_filter={"notvalid": "not a region"},
            destination_type=self.rack_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY
        )

        with self.assertRaises(ValidationError):
            m2m.clean()

    def test_clean_same_object(self):
        m2m = Relationship(
            name="Another Vlan to Rack",
            slug="vlan-rack-2",
            source_type=self.rack_ct,
            destination_type=self.rack_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY
        )

        with self.assertRaises(ValidationError):
            m2m.clean()

    def test_clean_valid(self):
        m2m = Relationship(
            name="Another Vlan to Rack",
            slug="vlan-rack-2",
            source_type=self.site_ct,
            source_filter={"region": "myregion"},
            destination_type=self.rack_ct,
            destination_filter={"site": "mysite"},
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY
        )

        m2m.clean()

        self.assertTrue(True)

    def test_get_label_input(self):
        with self.assertRaises(ValueError):
            self.m2m_1.get_label("wrongside")

    def test_get_label_with_label(self):
        self.assertEqual(self.m2m_1.get_label("source"), "My Vlans")
        self.assertEqual(self.m2m_1.get_label("destination"), "My Racks")

    def test_get_label_without_label_defined(self):
        self.assertEqual(self.m2m_2.get_label("source"), "VLANs")
        self.assertEqual(self.m2m_2.get_label("destination"), "racks")

    def test_has_many_input(self):
        with self.assertRaises(ValueError):
            self.m2m_1.has_many("wrongside")

    def test_has_many(self):
        self.assertTrue(self.m2m_1.has_many("source"))
        self.assertTrue(self.m2m_1.has_many("destination"))
        self.assertFalse(self.o2m_1.has_many("source"))
        self.assertTrue(self.m2m_1.has_many("destination"))
        self.assertFalse(self.o2o_1.has_many("source"))
        self.assertFalse(self.o2o_1.has_many("destination"))

    def test_to_form_field_m2m(self):

        field = self.m2m_1.to_form_field("source")
        self.assertFalse(field.required)
        self.assertIsInstance(field, DynamicModelMultipleChoiceField)
        self.assertEqual(field.label, "My Vlans")
        self.assertEqual(field.query_params, {})

        field = self.m2m_1.to_form_field("destination")
        self.assertFalse(field.required)
        self.assertIsInstance(field, DynamicModelMultipleChoiceField)
        self.assertEqual(field.label, "My Racks")
        self.assertEqual(field.query_params, {"site": "mysite"})

    def test_to_form_field_o2m(self):

        field = self.o2m_1.to_form_field("source")
        self.assertFalse(field.required)
        self.assertIsInstance(field, DynamicModelMultipleChoiceField)
        self.assertEqual(field.label, "VLANs")

        field = self.o2m_1.to_form_field("destination")
        self.assertFalse(field.required)
        self.assertIsInstance(field, DynamicModelChoiceField)
        self.assertEqual(field.label, "site")


class RelationshipAssociationTest(RelationshipBaseTest):

    # def test_clean_type(self):
    #     # Create with the wrong source Type
    #     with self.assertRaises(ValidationError):
    #         cra = RelationshipAssociation(relationship=self.m2m_1, source=self.sites[0], destination=self.vlans[0])
    #         cra.save()

    #     # Create with the wrong destination Type
    #     with self.assertRaises(ValidationError):
    #         cra = RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.racks[0])
    #         cra.save()

    def test_get_peer(self):
        cra = RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[0])
        cra.save()

        self.assertEqual(cra.get_peer(self.racks[0]), self.vlans[0])
        self.assertEqual(cra.get_peer(self.vlans[0]), self.racks[0])
        self.assertEqual(cra.get_peer(self.vlans[1]), None)
