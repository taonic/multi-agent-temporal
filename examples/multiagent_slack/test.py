
from pydantic import BaseModel, create_model
import inspect
from types import FunctionType
from typing import Optional, List, Callable, Union, Literal
from vertexai.generative_models import FunctionDeclaration
from google.adk.tools._automatic_function_calling_util import build_function_declaration

# Example Pydantic model for a User
class User(BaseModel):
    id: int
    name: str
    email: str
    age: Optional[int] = None
    hobbies: List[str] = []
    
# Example usage
def test_user_model():
    print(build_function_declaration(User))
    
    # Create a valid user
    user1 = User(
        id=1,
        name="John Doe",
        email="john@example.com",
        age=30,
        hobbies=["reading", "coding"]
    )
    
    # Create user with only required fields
    user2 = User(
        id=2,
        name="Jane Doe", 
        email="jane@example.com"
    )
    
    # Validate the models
    assert user1.id == 1
    assert user2.age is None
    assert len(user1.hobbies) == 2
    
    # Test model conversion to dict
    user1_dict = user1.model_dump()
    assert isinstance(user1_dict, dict)
    
if __name__ == "__main__":
    test_user_model()