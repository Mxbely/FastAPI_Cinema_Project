from typing import Type, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import (
    Cart,
    CartItem,
    Movie,
    Order,
    User,
    OrderItem,
    Payment,
    PaymentItem,
    PaymentStatusEnum
)
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


def delete_cart_item_by_cart(db: Session, cart_id: int) -> None:
    db.query(CartItem).filter(CartItem.cart_id == cart_id).delete()
    db.commit()


def create_order(db: Session, order: Order) -> None:
    db.add(order)
    db.commit()
    db.refresh(order)


def create_order_items(db: Session, order: Order, cart: Cart) -> List[OrderItem]:
    order_items: List[OrderItem] = []
    for item in cart.items:
        order_item = OrderItem(
            order_id=order.id,
            movie_id=item.movie.id,
            price_at_order=item.movie.price
        )
        db.add(order_item)
        order_items.append(order_item)

    db.commit()
    return order_items


def create_payment(db: Session, user: User, order: Order) -> Payment:
    payment = Payment(
        user_id=user.id,
        order_id=order.id,
        status=PaymentStatusEnum.PENDING,
        amount=order.total_amount,
        external_payment_id=None
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def create_payment_items(db: Session, payment: Payment, order_items: List[OrderItem]) -> None:
    for order_item in order_items:
        payment_item = PaymentItem(
            payment_id=payment.id,
            order_item_id=order_item.id,
            price_at_payment=order_item.price_at_order
        )
        db.add(payment_item)

    db.commit()


def process_order_payment_and_clear_cart(db: Session, user: User, order: Order, cart: Cart) -> Payment:
    order_items = create_order_items(db, order, cart)
    payment = create_payment(db, user, order)
    create_payment_items(db, payment, order_items)

    delete_cart_item_by_cart(db, cart.id)

    return payment


def is_movie_in_any_cart(db: Session, movie_id: int) -> bool:
    return db.query(CartItem).filter(CartItem.movie_id == movie_id).count() > 0


def delete_movie(db: Session, movie: Movie) -> None:
    db.delete(movie)
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
