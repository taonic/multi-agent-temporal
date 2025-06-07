import inspect
from dataclasses import fields, is_dataclass
from typing import get_type_hints, get_origin, get_args, Union, List, Dict, Any
from vertexai.generative_models import FunctionDeclaration, Tool

def create_function_declaration_with_dataclass_support(func: callable) -> FunctionDeclaration:
    """
    Create a FunctionDeclaration that properly handles dataclass arguments.

    This function validates that the input function has exactly one parameter
    which is a dataclass type. If these conditions are not met, it raises
    a ValueError.

    Args:
        func: The function to convert to a FunctionDeclaration

    Returns:
        FunctionDeclaration with proper dataclass parameter handling

    Raises:
        ValueError: If function doesn't have exactly one dataclass parameter
    """

    # Get function signature and type hints
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    # Filter out 'self' parameter for methods
    params = [param for name, param in sig.parameters.items() if name != 'self']
    param_names = [name for name in sig.parameters.keys() if name != 'self']

    # Validate that there's exactly one parameter
    if len(params) != 1:
        raise ValueError(
            f"Function {func.__name__} must have exactly one parameter "
            f"(excluding 'self'), but has {len(params)} parameters: {param_names}"
        )

    param_name = param_names[0]
    param = params[0]
    param_type = type_hints.get(param_name, param.annotation)

    # Handle Optional types - unwrap to get the actual type
    origin = get_origin(param_type)
    if origin is Union:
        args = get_args(param_type)
        # Check if it's Optional (Union with None)
        if len(args) == 2 and type(None) in args:
            param_type = args[0] if args[1] is type(None) else args[1]

    # Validate that the parameter is a dataclass
    if not is_dataclass(param_type):
        raise ValueError(
            f"Function {func.__name__} parameter '{param_name}' must be a dataclass type, "
            f"but got {param_type}"
        )

    # Get function docstring for description
    doc = inspect.getdoc(func) or f"Function {func.__name__}"

    # For dataclass parameters, we flatten the dataclass fields into the function parameters
    # This allows the LLM to understand and provide all the dataclass fields directly
    dataclass_schema = _dataclass_to_schema(param_type)

    # The parameters schema is the dataclass schema itself
    parameters = {
        "title": func.__name__,
        "type": "object",
        "properties": {
            param_name: {
                "title": param_name,
                "type": "object",
                "properties": dataclass_schema["properties"],
                "required": dataclass_schema["required"]
            }
        },
        "required": [param_name]
    }

    # Add information about the original dataclass to the description
    enhanced_doc = f"{doc}\n\nThis function takes a {param_type.__name__} dataclass parameter."
    if param_type.__doc__:
        enhanced_doc += f"\n{param_type.__name__}: {param_type.__doc__.strip()}"

    return FunctionDeclaration(
        name=func.__name__,
        description=enhanced_doc,
        parameters=parameters
    )

def create_function_declaration_from_dataclass(dataclass_type: type, function_name: str = None) -> FunctionDeclaration:
    """
    Create a FunctionDeclaration directly from a dataclass type.
    
    This is useful when you want to define a tool schema using a dataclass
    without requiring a wrapper function.

    Args:
        dataclass_type: The dataclass type to convert to a FunctionDeclaration
        function_name: Optional name for the function. If not provided, uses the dataclass name

    Returns:
        FunctionDeclaration representing the dataclass schema

    Raises:
        ValueError: If the provided type is not a dataclass
    """
    if not is_dataclass(dataclass_type):
        raise ValueError(f"{dataclass_type} is not a dataclass")

    name = function_name or dataclass_type.__name__
    doc = dataclass_type.__doc__ or f"Schema for {dataclass_type.__name__}"
    
    # Get the dataclass schema
    dataclass_schema = _dataclass_to_schema(dataclass_type)
    
    # Create parameters schema - the dataclass fields become the function parameters
    parameters = {
        "title": name,
        "type": "object",
        "properties": dataclass_schema["properties"],
        "required": dataclass_schema["required"]
    }

    return FunctionDeclaration(
        name=name,
        description=doc,
        parameters=parameters
    )

def _convert_type_to_schema(param_type: Any, param_name: str) -> Dict[str, Any]:
    """
    Convert a Python type (including dataclasses) to JSON schema.

    Args:
        param_type: The Python type to convert
        param_name: Name of the parameter (for error messages)

    Returns:
        Dictionary representing the JSON schema for this type
    """

    # Handle dataclass types
    if is_dataclass(param_type):
        return _dataclass_to_schema(param_type)

    # Handle basic types
    if param_type == str:
        return {"type": "string"}
    elif param_type == int:
        return {"type": "integer"}
    elif param_type == float:
        return {"type": "number"}
    elif param_type == bool:
        return {"type": "boolean"}
    elif param_type == Any:
        return {"type": "string", "description": "Any type of value"}

    # Handle List types
    origin = get_origin(param_type)
    if origin is list or origin is List:
        args = get_args(param_type)
        if args:
            item_schema = _convert_type_to_schema(args[0], f"{param_name}_item")
            return {
                "type": "array",
                "items": item_schema
            }
        else:
            return {"type": "array"}

    # Handle Dict types
    if origin is dict or origin is Dict:
        return {"type": "object"}

    # Handle Union types (including Optional)
    if origin is Union:
        args = get_args(param_type)
        # Check if it's Optional (Union with None)
        if len(args) == 2 and type(None) in args:
            non_none_type = args[0] if args[1] is type(None) else args[1]
            schema = _convert_type_to_schema(non_none_type, param_name)
            # Mark as optional by not including in required fields
            return schema
        else:
            # For other Union types, use the first type
            return _convert_type_to_schema(args[0], param_name)

    # Default to string for unknown types
    return {
        "type": "string",
        "description": f"Parameter {param_name} of type {param_type}"
    }

def _dataclass_to_schema(dataclass_type: type) -> Dict[str, Any]:
    """
    Convert a dataclass to JSON schema.

    Args:
        dataclass_type: The dataclass type to convert

    Returns:
        Dictionary representing the JSON schema for the dataclass
    """
    if not is_dataclass(dataclass_type):
        raise ValueError(f"{dataclass_type} is not a dataclass")

    schema = {
        "type": "object",
        "properties": {},
        "required": [],
        "description": f"Object of type {dataclass_type.__name__}"
    }

    # Add description from docstring if available
    if dataclass_type.__doc__:
        schema["description"] = dataclass_type.__doc__.strip()

    # Process each field in the dataclass
    for field in fields(dataclass_type):
        field_schema = _convert_type_to_schema(field.type, field.name)
        field_schema["title"] = field.name

        # Add field description if available
        if hasattr(field, 'metadata') and 'description' in field.metadata:
            field_schema["description"] = field.metadata['description']

        schema["properties"][field.name] = field_schema

        # Add to required if no default value
        if field.default == dataclass_type.__dataclass_fields__[field.name].default_factory:
            if field.default_factory == dataclass_type.__dataclass_fields__[field.name].default_factory:
                schema["required"].append(field.name)

    return schema

def create_enhanced_tool(functions: List[callable], sub_agents: Dict[str, type] = None) -> Tool:
    """
    Create a Tool with enhanced dataclass support.
    
    Can handle callable functions, dataclass types, and a dictionary of sub-agents.

    Args:
        items: List of functions and/or dataclass types to include in the tool
        sub_agents: Optional dictionary mapping agent names to their dataclass schemas

    Returns:
        Tool object with proper dataclass handling
    """
    function_declarations = []

    # Process regular items (functions and standalone dataclasses)
    for item in functions:
        try:
            if callable(item):
                # Handle callable function
                try:
                    # Try using the enhanced declaration first for functions with dataclass params
                    declaration = create_function_declaration_with_dataclass_support(item)
                    function_declarations.append(declaration)
                except ValueError:
                    # Fallback to the original method for regular functions
                    declaration = FunctionDeclaration.from_func(item)
                    function_declarations.append(declaration)
            else:
                print(f"Warning: Unsupported item type {type(item)} for {item}")
                continue
                
        except Exception as e:
            print(f"Error: Could not create declaration for {item}: {e}")
            continue

    # Process sub-agents dictionary
    if sub_agents:
        for agent_name, schema_class in sub_agents.items():
            try:
                if not is_dataclass(schema_class):
                    print(f"Warning: Sub-agent '{agent_name}' schema must be a dataclass, got {type(schema_class)}")
                    continue
                    
                declaration = create_function_declaration_from_dataclass(
                    dataclass_type=schema_class,
                    function_name=agent_name
                )
                function_declarations.append(declaration)
                
            except Exception as e:
                print(f"Error: Could not create declaration for sub-agent {agent_name}: {e}")
                continue

    return Tool(function_declarations=function_declarations)