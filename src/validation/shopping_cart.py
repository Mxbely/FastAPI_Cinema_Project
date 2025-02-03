from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import Cart, CartItem, Movie, User


def validate_movie_availability(movie: Movie):
    if not movie:
        raise HTTPException(
            status_code=400,
            detail="Movie is not available for purchase."
        )


def validate_not_purchased(user: User, movie: Movie, db: Session):
    purchased_movies = db.query(CartItem).join(Cart).filter(
        Cart.user_id == user.id,
        CartItem.movie_id == movie.id
    ).first()
    if purchased_movies:
        raise HTTPException(
            status_code=400,
            detail="You have already purchased this movie."
        )


def validate_not_in_cart(user: User, movie: Movie, db: Session):
    cart = db.query(Cart).filter(Cart.user_id == user.id).first()
    if cart:
        existing_item = db.query(CartItem).filter(
            CartItem.cart_id == cart.id,
            CartItem.movie_id == movie.id
        ).first()
        if existing_item:
            raise HTTPException(
                status_code=400,
                detail="Movie already in cart."
            )
