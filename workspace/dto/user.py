from pydantic import BaseModel, EmailStr


class UserDto(BaseModel):
    username: str
    email: EmailStr
    password: str
