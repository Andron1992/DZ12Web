from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import schemas, crud, auth

# Налаштування OAuth2 для авторизації через токен
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

# Реєстрація нового користувача
@app.post("/register/", response_model=schemas.UserResponse, status_code=201)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=409, detail="Email already registered")
    return crud.create_user(db=db, user=user)

# Отримання токену (логін)
@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = auth.create_access_token(data={"sub": user.email})
    refresh_token = auth.create_refresh_token(data={"sub": user.email})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

# Отримання нового access_token за допомогою refresh_token
@app.post("/refresh_token", response_model=schemas.Token)
def refresh_access_token(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(refresh_token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = crud.get_user_by_email(db, email=email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    new_access_token = auth.create_access_token(data={"sub": user.email})
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


@app.post("/contacts/", response_model=schemas.ContactResponse)
async def create_contact(contact: schemas.ContactCreate, db: Session = Depends(get_db),
                         token: str = Depends(oauth2_scheme)):
    # Отримуємо поточного користувача з токену
    current_user = await auth.get_current_user(token, db)

    # Створюємо контакт для поточного користувача
    return crud.create_contact(db=db, contact=contact, user_id=current_user.id)


# Отримання контактів для авторизованого користувача
@app.get("/contacts/", response_model=List[schemas.ContactResponse])
async def read_contacts(skip: int = 0, limit: int = 10, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    current_user = await auth.get_current_user(token, db)  # Викликаємо корутину
    return crud.get_contacts_for_user(db, user_id=current_user.id, skip=skip, limit=limit)


# Отримання конкретного контакту (авторизовані користувачі)
@app.get("/contacts/{contact_id}", response_model=schemas.ContactResponse)
async def read_contact(contact_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    current_user = await auth.get_current_user(token, db)  # Викликаємо корутину
    db_contact = crud.get_contact_by_id(db, contact_id=contact_id)
    if db_contact is None or db_contact.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Contact not found or access denied")
    return db_contact

# Оновлення контактів (авторизовані користувачі)
@app.put("/contacts/{contact_id}", response_model=schemas.ContactResponse)
async def update_contact(contact_id: int, contact: schemas.ContactUpdate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    current_user = await auth.get_current_user(token, db)  # Викликаємо корутину через await
    db_contact = crud.get_contact_by_id(db, contact_id=contact_id)
    if db_contact is None or db_contact.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Contact not found or access denied")
    return crud.update_contact(db, contact_id, contact)


# Видалення контактів (авторизовані користувачі)
@app.delete("/contacts/{contact_id}")
async def delete_contact(contact_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    current_user = await auth.get_current_user(token, db)  # Викликаємо корутину через await
    db_contact = crud.get_contact_by_id(db, contact_id=contact_id)
    if db_contact is None or db_contact.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Contact not found or access denied")
    crud.delete_contact(db, contact_id)
    return {"message": "Contact deleted successfully"}

