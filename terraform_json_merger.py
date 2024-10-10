import json
import os


def find_planned_values_and_changes(data, file_path):
    # Dictionary to store extracted data from the file
    extracted_data = {"resources": [], "child_modules": [], "resource_changes": []}

    if isinstance(data, dict):
        # Add top-level keys if they exist
        # extract metadata
        for key in ["format_version", "terraform_version", "variables"]:
            extracted_data[key] = data.get(key, None)

        # Handle planned values
        planned_values = data.get("planned_values", {})
        root_module = planned_values.get("root_module", {})

        # Adds the root-level resources from root_module to the resources list in extracted_data
        extracted_data["resources"].extend(root_module.get("resources", []))

        # Collect child_modules resources recursively from modules nested under the root module
        def extract_child_module_resources(module):
            child_resources = []
            child_modules = module.get("child_modules", [])
            for child_module in child_modules:
                if "resources" in child_module:
                    child_resources.extend(child_module["resources"])
                # Recursively extract resources from nested child modules
                child_resources.extend(extract_child_module_resources(child_module))
            return child_resources
        
        # Collect all child module resources
        child_module_resources = extract_child_module_resources(root_module)
        extracted_data["child_modules"].extend(child_module_resources)

        # Collect resource_changes excluding "no-op"
        # "no-op" means no operation (no real changes), only real changes are added
        # https://developer.hashicorp.com/terraform/internals/json-format#plan-representation
        resource_changes = data.get("resource_changes", [])
        extracted_data["resource_changes"].extend(
            [change for change in resource_changes if "no-op" not in change["change"]["actions"]]
        )
    # if data is not real dict (not valid JSON) print error message
    else:
        print(f"Expected dict, but received {type(data)} in file: {file_path}")

    return extracted_data


def process_tfplan_files(directory):
    combined_data = {} # store final data
    all_resources = []
    all_child_module_resources = []
    all_resource_changes = []

    # Walk through the directory to find all "tfplan.json" files
    for root, _, files in os.walk(directory):
        for file in files:
            if file == "tfplan.json":
                file_path = os.path.join(root, file)
                print(f"Processing file: {file_path}")
                
                try:
                    # Load the JSON data from the file
                    with open(file_path, "r") as json_file:
                        json_data = json.load(json_file)
                    
                    # Calls the earlier function to extract the resources, child modules, and resource changes from this file.
                    extracted_data = find_planned_values_and_changes(json_data, file_path)
                    
                    # Initialize combined_data with top-level fields if not already initialized
                    if not combined_data:
                        combined_data.update({
                            "format_version": extracted_data.get("format_version"),
                            "terraform_version": extracted_data.get("terraform_version"),
                            "variables": extracted_data.get("variables"),
                            "planned_values": {
                                "root_module": {"resources": [], "child_modules": []}
                            },
                            "resource_changes": []
                        }) # Initializes the structure of combined_data to hold the root module and child module resources, along with resource changes.

                    # Append resources
                    all_resources.extend(extracted_data.get("resources", []))
                    all_child_module_resources.extend(extracted_data.get("child_modules", []))
                    all_resource_changes.extend(extracted_data.get("resource_changes", []))
                
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Error processing file {file_path}: {str(e)}")
    
    # Collects all the extracted resources, child module resources, and resource changes and adds them to the final combined_data structure.
    combined_data["planned_values"]["root_module"]["resources"] = all_resources
    if all_child_module_resources:
        combined_data["planned_values"]["root_module"]["child_modules"] = [{"resources": all_child_module_resources}]
    combined_data["resource_changes"] = all_resource_changes

    return combined_data


# Directory containing the tfplan.json files
json_path_file = "/Users/gkolev/Downloads/plans/"
# Process and extract planned values and resource changes
all_planned_values = process_tfplan_files(json_path_file)

# Save the combined planned values and resource changes to a new JSON file
output_file = "/Users/gkolev/Downloads/plans/now.json"
with open(output_file, "w") as outfile:
    json.dump(all_planned_values, outfile, indent=4)

print(f"Planned values and resource changes found and saved to: {output_file}")
