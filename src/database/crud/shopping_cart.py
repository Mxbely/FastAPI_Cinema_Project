from sqlalchemy.orm import Session

from database import (
    Cart,
    User,
    Movie,
    CartItem
)


def get_user_cart(user: User, db: Session):
    return db.query(Cart).filter(Cart.user_id == user.id).first()


def get_movie_by_id(movie_id: int, db: Session):
    return db.query(Movie).filter(Movie.id == movie_id).first()


def get_cart_item(cart: Cart, movie_id: int, db: Session):
    return db.query(CartItem).filter(
        CartItem.cart_id == cart.id, CartItem.movie_id == movie_id
    ).first()


def create_cart(user: User, db: Session):
    cart = Cart(user_id=user.id)
    db.add(cart)
    db.flush()
    return cart


def add_cart_item(cart: Cart, movie: Movie, db: Session):
    cart_item = CartItem(cart_id=cart.id, movie_id=movie.id)
    db.add(cart_item)
    db.commit()


def delete_cart_item(cart_item: CartItem, db: Session):
    db.delete(cart_item)
    db.commit()
