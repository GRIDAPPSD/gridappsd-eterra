import json
import logging
import argparse

#from gridappsd.topics import fncs_input_topic, fncs_output_topic
# from typing import List, Dict, Union, Any

out_json = list()

'''Dictionary for mapping the attribute values of control poitns for Capacitor, Regulator and Switches'''

attribute_map = {
    "capacitors": {
        "attribute": ["RegulatingControl.mode", "RegulatingControl.targetDeadband", "RegulatingControl.targetValue",
                      "ShuntCompensator.aVRDelay", "ShuntCompensator.sections"]}
    ,
    "switches": {
        "attribute": "Switch.open"
    }
    ,

    "regulators": {
        "attribute": ["RegulatingControl.targetDeadband", "RegulatingControl.targetValue", "TapChanger.initialDelay",
                      "TapChanger.lineDropCompensation", "TapChanger.step", "TapChanger.lineDropR",
                      "TapChanger.lineDropX"]}

}


class dnp3_mapping():
    """ This creates dnps input and ouput points for incoming CIM messages  and model dictionary file respectively."""

    def __init__(self, map_file):
        self.c_ao = 0
        self.c_bo = 0
        self.c_ai = 0
        self.c_bi = 0
        self.magnitude_value = None
        self.measurement_mRID = None

        with open(map_file, 'r') as f:
            self.file_dict = json.load(f)
            self.out_json = list()

    def on_message(self, headers, msg):
        """ This method handles incoming messages on the fncs_output_topic for the simulation_id.
        Parameters
        ----------
        headers: dict
            A dictionary of headers that could be used to determine topic of origin and
            other attributes.
        message: object
            A data structure following the protocol defined in the message structure
            of ``GridAPPSD``.  Most message payloads will be serialized dictionaries, but that is
            not a requirement.
        """
        message = {}
        try:
            message_str = 'received message ' + str(msg)

            json_msg = yaml.safe_load(str(msg))

            if type(json_msg) != dict:
                raise ValueError(
                    ' is not a json formatted string.'
                    + '\njson_msg = {0}'.format(json_msg))


            measurement_values = json_msg["message"]["measurements"]
            print(measurement_values)

            # storing the magnitude and measurement_mRID values to publish in the dnp3 points for measurement key values
            for y in measurement_values:
                self.magnitude_value = y.get["magnitude"]
                self.measurement_mRID = y.get["measurement_mrid"]

        except Exception as e:
            message_str = "An error occurred while trying to translate the  message received" + str(e)

    def assign_val_m(self, data_type, group, variation, index, name, description, measurement_type, measurement_id,
                     magnitude):
        """ Method is to initialize  parameters to be used for generating  output  points for measurement key values """
        records = dict()  # type: Dict[str, Any]
        records["data_type"] = data_type
        records["index"] = index
        records["group"] = group
        records["variation"] = variation
        records["description"] = description
        records["name"] = name
        records["measurement_type"] = measurement_type
        records["measurement_id"] = measurement_id
        records["magnitude"] = self.magnitude_value
        self.out_json.append(records)

    def assign_val(self, data_type, group, variation, index, name, description, measurement_type, measurement_id):
        """ This method is to initialize  parameters to be used for generating  output  points for output points"""
        records = dict()
        records["data_type"] = data_type
        records["index"] = index
        records["group"] = group
        records["variation"] = variation
        records["description"] = description
        records["name"] = name
        records["measurement_type"] = measurement_type
        records["measurement_id"] = measurement_id
        self.out_json.append(records)

    def assign_valc(self, data_type, group, variation, index, name, description, object_id, attribute):
        """ Method is to initialize  parameters to be used for generating  dnp3 control as Analog/Binary Input points"""
        records = dict()
        records["data_type"] = data_type
        records["index"] = index
        records["group"] = group
        records["variation"] = variation
        records["description"] = description
        records["name"] = name
        records["object_id"] = object_id
        records["attribute"] = attribute
        self.out_json.append(records)

    def load_json(self, out_json, out_file):
        with open(out_file, 'w') as fp:
            out_dict = dict({'points': out_json})
            json.dump(out_dict, fp, indent=2, sort_keys=True)

    def _create_dnp3_object_map(self):
        """This method creates the points by taking the input data from model dictionary file"""
        feeders = self.file_dict.get("feeders", [])
        for x in feeders:
            measurements = x.get("measurements", [])
            capacitors = x.get("capacitors", [])
            regulators = x.get("regulators", [])
            switches = x.get("switches", [])
            solarpanels = x.get("solarpanels", [])
            batteries = x.get("batteries", [])

        for m in measurements:
            measurement_type = m.get("measurementType")
            measurement_id = m.get("mRID")
            name = m.get("name")
            description = "Equipment is " + m['name'] + "," + m['ConductingEquipment_type'] + " and phase is " + m['phases']
            if m['MeasurementClass'] == "Analog" and self.measurement_mRID == measurement_id:
                # Checking if magnitude value in CIM message from output topic has a null value
                if self.magnitude_value is None:
                    self.assign_val("AO", 42, 3, self.c_ao, name, description, measurement_type, measurement_id)
                else:
                    self.assign_val_m("AO", 42, 3, self.c_ao, name, description, measurement_type, measurement_id, self.magnitude_value)
            self.c_ao += 1

            if m['MeasurementClass'] == "Discrete" and self.measurement_mRID == measurement_id:
                if self.magnitude_value is None:
                    self.assign_val("BO", 11, 1, self.c_bo, name, description, measurement_type,
                                    measurement_id)  # print the magnitude value if its not null
                else:
                    self.assign_val_m("BO", 11, 1, self.c_bo, name, description, measurement_type, measurement_id, self.magnitude_value)
                    self.c_bo += 1

        for m in capacitors:
            object_id = m.get("mRID")
            name = m.get("name")
            phase_value = list(m['phases'])
            description1 = "Capacitor, " + m['name'] + "," + "phase -" + m['phases']
            cap_attribute = attribute_map['capacitors']['attribute']  # type: List[str]
            for l in range(0, 4):
                # publishing attribute value for capacitors as Bianry/Analog Input points based on phase  attribute
                self.assign_valc("AI", 32, 3, self.c_ai, name, description1, object_id, cap_attribute[l])
                self.c_ai += 1
                for j in range(0, len(m['phases'])):
                    description = "Capacitor, " + m['name'] + "," + "phase -" + phase_value[j]
                    self.assign_valc("BI", 2, 1, self.c_bi, name, description, object_id, cap_attribute[4])
                    self.c_bi += 1

        for m in solarpanels:
            measurement_id = m.get("mRID")
            name = m.get("name")
            description = "Solarpanel " + m['name'] + "phases - " + m['phases']
            self.assign_val("AI", 32, 3, self.c_ai, name, description, None, measurement_id)
            self.c_ai += 1

        for m in batteries:
            measurement_id = m.get("mRID")
            name = m.get("name")
            description = "Battery, " + m['name'] + "phases - " + m['phases']
            self.assign_val("AI", 32, 3, self.c_ai, name, description, None, measurement_id)
            self.c_ai += 1

        for m in switches:
            object_id = m.get("mRID")
            name = m.get("name")
            for k in range(0, len(m['phases'])):
                phase_value = list(m['phases'])
                description = "Switch, " + m["name"] + "phases - " + phase_value[k]
                self.assign_valc("BI", 2, 1, self.c_bi, name, description, object_id,
                                 attribute_map['switches']['attribute'])
                self.c_bi += 1

        for m in regulators:
            name = m.get("bankName")
            reg_attribute = attribute_map['regulators']['attribute']
            bank_phase = list(m['bankPhases'])
            description = "Regulator, " + m['bankName'] + " " + "phase is  -  " + m['bankPhases']
            for n in range(0, 5):
                object_id = m.get("mRID")
                self.assign_valc("AI", 32, 3, self.c_ai, name, description, object_id[0], reg_attribute[n])
                self.c_ai += 1
                for i in range(4, 7):
                    reg_phase_attribute = attribute_map['regulators']['attribute'][i]
                for j in range(0, len(m['bankPhases'])):
                    description = "Regulator, " + m['tankName'][j] + " " "phase is  -  " + m['bankPhases'][j]
                    object_id = m.get("mRID")
                    self.assign_valc("AI", 32, 3, self.c_ai, name, description, object_id[j], reg_phase_attribute)
                    self.c_ai += 1

        return self.out_json


def _main(simulation_id, input_file=  None, out_file = None):
    print(" I am here ")
    outfile = dnp3_mapping(input_file)
    outfile.load_json(outfile._create_dnp3_object_map(), out_file)


def _get_opts():
    parser = argparse.ArgumentParser()
    parser.add_argument("simulation_id", help="The simulation id to use for responses on the message bus.")
    parser.add_argument("input_file", help='The input dictionary file with measurements.')
    parser.add_argument("out_file", help='The output json file having dnp3 points.')
    opts = parser.parse_args()
    return opts


if __name__ == "__main__":
    opts = _get_opts()
    print("Alka")
    simulation_id = opts.simulation_id
    out_file = opts.out_file
    _main(simulation_id, opts.input_file, opts.out_file)