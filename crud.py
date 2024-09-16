from fastapi import HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from models import Contact, User
from schemas import ContactCreate, ContactUpdate, UserCreate
from auth import get_password_hash

def create_user(db: Session, user: UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_contact(db: Session, contact: schemas.ContactCreate, user_id: int):
    # Перевіряємо, чи контакт з таким email вже існує
    existing_contact = db.query(models.Contact).filter_by(email=contact.email).first()
    if existing_contact:
        raise HTTPException(status_code=400, detail="Contact with this email already exists")

    # Якщо контакту з таким email немає, створюємо новий
    db_contact = models.Contact(**contact.dict(), owner_id=user_id)
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_contacts_for_user(db: Session, user_id: int, skip: int = 0, limit: int = 10):
    return db.query(Contact).filter(Contact.owner_id == user_id).offset(skip).limit(limit).all()


def get_contacts(db: Session, skip: int = 0, limit: int = 10):
    return db.query(Contact).offset(skip).limit(limit).all()


def get_contact_by_id(db: Session, contact_id: int):
    return db.query(Contact).filter(Contact.id == contact_id).first()


def update_contact(db: Session, contact_id: int, contact: ContactUpdate):
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if db_contact:
        for key, value in contact.dict(exclude_unset=True).items():
            setattr(db_contact, key, value)
        db.commit()
        db.refresh(db_contact)
    return db_contact


def delete_contact(db: Session, contact_id: int):
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if db_contact:
        db.delete(db_contact)
        db.commit()
    return db_contact
