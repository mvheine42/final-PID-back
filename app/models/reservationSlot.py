from pydantic import BaseModel
from datetime import time, date

class ReservationSlot(BaseModel):
    reservationDate: date
    reservationTime: str
    capacity: int = 4
    usedSlots: int = 0