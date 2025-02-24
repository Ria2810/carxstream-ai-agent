import json
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, ValidationError
from typing import Dict, Any

class PackageRequest(BaseModel):
    env: str = Field(..., description="Environment, e.g., DEV or PROD.")
    user_role: str = Field(..., description="User role, e.g., Dealer or User.")

class PackageShowingTool(BaseTool):
    name: str = "package_showing_tool"
    description: str = "Shows the packages available based on environment and user role. Input must be a JSON string."

    def _run(self, tool_input: str) -> Dict[str, Any]:
        if not tool_input.strip():
            return {"Error": "No input provided. Please provide a JSON input with 'env' and 'user_role'."}

        try:
            input_data = json.loads(tool_input)
        except json.JSONDecodeError as e:
            return {"Error": f"Invalid JSON input: {str(e)}. Input must be a valid JSON string like {{\"env\":\"DEV\",\"user_role\":\"Dealer\"}}."}

        try:
            request = PackageRequest(**input_data)
        except ValidationError as e:
            return {"Error": f"Validation error: {str(e)}. Please provide both 'env' and 'user_role' fields."}

        env = request.env.upper()
        user_role = request.user_role.capitalize()

        PACKAGES = {
            "DEV": {
                "Dealer": {"Saver": "2000 rs", "Premium": "5000 rs"},
                "User": {"Featured": "250 rs", "Popular": "500 rs"},
            },
            "PROD": {
                "Dealer": {
                    "Saver": "22500 rs",
                    "Silver": "5000 rs",
                    "Gold": "10000 rs",
                    "Platinum": "15000 rs",
                    "Diamond": "45000 rs",
                },
                "User": {"Featured": "250 rs", "Popular": "500 rs"},
            },
        }

        if env in PACKAGES and user_role in PACKAGES[env]:
            return PACKAGES[env][user_role]
        else:
            return {"Error": "No packages available for the specified environment or user role."}

    async def _arun(self, tool_input: str) -> Dict[str, Any]:
        raise NotImplementedError("Async is not implemented for this tool.")

package_list = PackageShowingTool()
