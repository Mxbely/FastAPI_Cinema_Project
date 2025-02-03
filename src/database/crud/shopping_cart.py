from typing import Type

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import Cart, CartItem, Movie, Order, User
from schemas.shopping_cart import CartItemDetail


def get_user_cart(user: User, db: Session) -> Cart | None:
    return db.query(Cart).filter(Cart.user_id == user.id).first()


def get_movie_by_id(movie_id: int, db: Session) -> Movie | None:
    return db.query(Movie).filter(Movie.id == movie_id).first()


def get_cart_item(cart: Cart, movie_id: int, db: Session) -> CartItem | None:
    return db.query(CartItem).filter(
        CartItem.cart_id == cart.id, CartItem.movie_id == movie_id
    ).first()


def create_cart(user: User, db: Session) -> Cart:
    cart = Cart(user_id=user.id)
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return cart


def add_cart_item(cart: Cart, movie: Movie, db: Session) -> CartItem:
    existing_item = get_cart_item(cart, movie.id, db)
    if existing_item:
        raise HTTPException(status_code=400, detail="Movie is already in the cart")

    cart_item = CartItem(cart_id=cart.id, movie_id=movie.id)
    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)
    return cart_item


def delete_cart_item(cart_item: CartItem, db: Session) -> None:
    db.delete(cart_item)
    db.commit()


def get_purchased_movies_from_db(user: User, db: Session) -> list[Type[Movie]]:
    return (
        db.query(Movie)
        .join(CartItem)
        .join(Cart)
        .join(Order, Order.user_id == Cart.user_id)
        .filter(Order.user_id == user.id)
        .distinct()
        .all()
    )


def get_cart_items_details(cart):
    return [
        CartItemDetail(
            movie_id=item.movie.id,
            title=item.movie.name,
            price=item.movie.price,
            genre=item.movie.genres[0].name if item.movie.genres else "Unknown",
            release_year=item.movie.year
        )
        for item in cart.items
    ] if cart else []
