from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str
    role: str = "employee"

class UserLogin(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

