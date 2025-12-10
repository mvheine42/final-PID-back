from datetime import date
from pydantic import BaseModel

class UserLogin(BaseModel):
    email: str
    password: str

class UserRegister(BaseModel):
    uid: str
    name: str
    birthday: str
    imageUrl: str

class UserForgotPassword(BaseModel):
    email: str

class TokenData(BaseModel):
    id_token: str

