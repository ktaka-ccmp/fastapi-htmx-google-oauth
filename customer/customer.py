from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from data.db import Customer, CustomerBase, get_db

router = APIRouter()

def get_customer(db_session: Session, customer_id: int):
    return db_session.query(Customer).filter(Customer.id==customer_id).first()

@router.get("/customer/")
def read_customers(db: Session = Depends(get_db)):
    q = db.query(Customer).offset(0).limit(100).all()
    result = { "description" : "hello", "results" : q}
    return result

@router.get("/customer/{customer_id}")
def read_customer(customer_id: int, db_session: Session = Depends(get_db)):
    todo = get_customer(db_session, customer_id)
    return todo

@router.post("/customer/")
def create_customer(customer: CustomerBase, db_session: Session = Depends(get_db)):
    db_customer = Customer(name=customer.name, email=customer.email)
    db_session.add(db_customer)
    db_session.commit()
    db_session.refresh(db_customer)
    return db_customer

@router.delete("/customer/{customer_id}")
async def delete_customer(customer_id: int, db_session: Session = Depends(get_db)):
    todo = get_customer(db_session, customer_id)
    db_session.delete(todo)
    db_session.commit()
