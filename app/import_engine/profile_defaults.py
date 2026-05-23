DEFAULT_IMPORT_PROFILES = [
    {
        "tenant_id": "tenant_a",
        "name": "default_users",
        "description": "Default user import profile for CSV or Excel files with user roster columns.",
        "is_default": True,
        "filename_contains": ["user", "users", "employee", "employees"],
        "required_headers": ["Email Address", "Age", "Department", "Full Name"],
        "sheet_mapping": {"csv": ["UserModel"], "Users": ["UserModel"], "Employees": ["UserModel"]},
        "model_definitions": [
            {
                "name": "UserModel",
                "table": "users",
                "fields": [
                    {
                        "name": "email",
                        "type": "str",
                        "required": True,
                        "unique": True,
                        "regex": r"^[^@]+@[^@]+\.[^@]+$",
                        "aliases": ["Email Address"],
                    },
                    {"name": "age", "type": "int", "required": False},
                    {"name": "department", "type": "str", "required": False, "aliases": ["Department"]},
                    {"name": "first_name", "type": "str", "required": False},
                    {"name": "last_name", "type": "str", "required": False},
                ],
                "transformations": [
                    {"type": "split", "source": "Full Name", "delimiter": " ", "targets": ["first_name", "last_name"]},
                    {"type": "lowercase", "source": "email", "target": "email"},
                ],
            }
        ],
    }
]
