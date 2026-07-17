import os
import yaml
from typing import Dict, Optional, Tuple


class YAMLManager:
    """Manages creation, loading, saving, and validation of YAML extraction schema files."""

    DEFAULT_TEMPLATE = {
        "statement": {
            "fields": {
                "account_number": {
                    "prompt": {
                        "description": "unique identifier for the customer account",
                        "format": "unique string, **always** formatted as a string",
                        "identifiers": ["Account Number"],
                        "instructions": "- This number uniquely identifies the user with the invoicer\n  - Account Number is **never** missing a label",
                        "type": "str",
                    }
                },
                "amount_due": {
                    "prompt": {
                        "description": "numerical value representing the amount that the customer owes",
                        "identifiers": ["Amount Due"],
                        "instructions": "- This is the total amount due by the customer, including previous balance and current charges",
                        "type": ["int", "float"],
                    }
                },
                "due_date": {
                    "prompt": {
                        "description": "date when payment is due from the customer",
                        "format": "YYYY-mm-dd date string",
                        "identifiers": ["Due Date"],
                        "instructions": "- Dates within this bill are **extremely unlikely** to be more than 1 year apart from each other. If you find this to be the case, consider whether you are seeing a year vs a day (e.g. 2/23 being Feb 23 instead of Feb 2023).",
                        "type": "str",
                    }
                },
                "provider_name": {
                    "prompt": {
                        "description": "name of the company that issued the statement or invoice and is owed payment from the customer",
                        "identifiers": ["Remit Payment"],
                        "instructions": "- This is the provider that receives payment, not necessarily the provider who issues the bill",
                        "type": "str",
                    }
                },
                "service_address": {
                    "prompt": {
                        "description": "the location where the services are consumed by the customer",
                        "identifiers": ["Mail To"],
                        "instructions": "- This is the location where the customer receives mail",
                        "type": "str",
                    }
                },
            }
        }
    }

    def __init__(self, yaml_dir: str = "prompts"):
        """Initialize with the directory where YAML schemas are stored."""
        self.yaml_dir = yaml_dir

    def create_new(self, file_name: str, content: Optional[Dict] = None) -> bool:
        """Create a new YAML file, optionally with custom content (defaults to DEFAULT_TEMPLATE)."""
        if not os.path.exists(self.yaml_dir):
            try:
                os.makedirs(self.yaml_dir)
            except OSError as e:
                print(f"Error creating directory {self.yaml_dir}: {str(e)}")
                return False
        file_path = os.path.join(self.yaml_dir, file_name)
        if content is None:
            content = self.DEFAULT_TEMPLATE
        try:
            with open(file_path, "w") as f:
                yaml.dump(content, f, default_flow_style=False)
            return True
        except Exception as e:
            print(f"Error creating YAML file: {str(e)}")
            return False

    @staticmethod
    def validate_filename(name: str) -> Tuple[bool, str]:
        """Check that the filename is non-empty and has a .yaml or .yml extension."""
        if not name:
            return False, "File name cannot be empty"
        if not name.endswith((".yaml", ".yml")):
            return False, "File name must end with .yaml or .yml"
        return True, ""

    def load_content(self, file_name: str) -> Optional[Dict]:
        """Load and parse a YAML file by name from the configured directory."""
        file_path = os.path.join(self.yaml_dir, file_name)
        try:
            with open(file_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading YAML file: {str(e)}")
            return None

    def load_raw(self, file_name: str) -> Optional[str]:
        """Return the raw text of a YAML file, or ``None`` if it cannot be read."""
        file_path = os.path.join(self.yaml_dir, file_name)
        try:
            with open(file_path) as f:
                return f.read()
        except Exception as e:
            print(f"Error reading YAML file: {str(e)}")
            return None

    def save_content(self, file_name: str, content: Dict) -> bool:
        """Write a dictionary to a YAML file in the configured directory."""
        file_path = os.path.join(self.yaml_dir, file_name)
        try:
            with open(file_path, "w") as f:
                yaml.dump(content, f, default_flow_style=False)
            return True
        except Exception as e:
            print(f"Error saving YAML file: {str(e)}")
            return False

    def edit_and_save(self, file_name: str, yaml_text: str) -> Tuple[bool, str]:
        """Parse a YAML text string and persist it to the file. Returns success status and a message."""
        try:
            parsed = yaml.safe_load(yaml_text)
            if self.save_content(file_name, parsed):
                return True, f"Successfully saved changes to {file_name}"
            return False, "Failed to save YAML file"
        except yaml.YAMLError as e:
            return False, f"Invalid YAML format: {str(e)}"
