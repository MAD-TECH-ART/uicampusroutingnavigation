import unittest

from osm_campus_places import parse_named_places, validate_places


class OSMCampusPlacesTests(unittest.TestCase):
    def test_named_features_include_numeric_latitude_and_longitude(self):
        xml_data = b"""
        <osm>
          <node id='1' lat='7.44' lon='3.89'><tag k='name' v='Gate'/></node>
          <node id='2' lat='7.45' lon='3.90'/>
          <way id='3'><nd ref='1'/><nd ref='2'/><tag k='name' v='Road'/></way>
        </osm>
        """
        places = parse_named_places(xml_data)
        validate_places(places)
        self.assertEqual(len(places), 2)
        self.assertTrue(all(isinstance(place["latitude"], float) for place in places))
        self.assertTrue(all(isinstance(place["longitude"], float) for place in places))

    def test_incomplete_coordinates_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_places([{"id": "way/1", "latitude": None, "longitude": 3.9}])


if __name__ == "__main__":
    unittest.main()