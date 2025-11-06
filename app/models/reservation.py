from pydantic import BaseModel, EmailStr
from datetime import date

class Reservation(BaseModel):
    customerName: str
    userEmail: EmailStr
    amountOfPeople: int
    reservationDate: date
    reservationTime: str