from http import HTTPStatus

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from user_todo_api.database import get_session
from user_todo_api.models import User
from user_todo_api.schemas import (
    MessageSchema,
    Token,
    UserList,
    UserPublicSchema,
    UserSchema,
)
from user_todo_api.security import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)

app = FastAPI()


@app.post('/users/', status_code=HTTPStatus.CREATED, response_model=UserPublicSchema)
def create_user(user: UserSchema, session: Session = Depends(get_session)):
    db_user = session.scalar(
        select(User).where((User.username == user.username) | (User.email == user.email))
    )

    if db_user:
        if db_user.username == user.username:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail='Username already exists',
            )
        elif db_user.email == user.email:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail='Email already exists',
            )

    db_user = User(
        username=user.username, password=get_password_hash(user.password), email=user.email
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return db_user


@app.get('/users/', response_model=UserList)
def read_users(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
):
    users = session.scalars(select(User).offset(skip).limit(limit)).all()
    return {'users': users}


@app.get('/users/{user_id}', response_model=UserPublicSchema)
def read_user(user_id: int, session: Session = Depends(get_session)):
    db_user = session.get(User, user_id)

    if not db_user:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='User not found')

    return db_user


@app.put('/users/{user_id}', response_model=UserPublicSchema)
def update_user(
    user_id: int,
    user: UserSchema,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='Not enough permissions')

    current_user.username = user.username
    current_user.password = get_password_hash(user.password)
    current_user.email = user.email
    session.commit()
    session.refresh(current_user)

    return current_user


@app.delete('/users/{user_id}', response_model=MessageSchema)
def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='Not enough permissions')

    session.delete(current_user)
    session.commit()

    return {'message': 'User deleted'}


@app.post('/token', response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    user = session.scalar(select(User).where(User.email == form_data.username))

    if not user:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail='Incorrect email or password'
        )

    if not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail='Incorrect email or password'
        )

    access_token = create_access_token(data={'sub': user.email})

    return {'access_token': access_token, 'token_type': 'bearer'}
