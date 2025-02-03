from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config import get_jwt_auth_manager
from database import (
    CartItem,
    Movie,
    Order,
    OrderItem,
    Payment,
    PaymentItem,
    PaymentStatusEnum,
    User,
    UserGroupEnum,
)
from database.crud.shopping_cart import (
    add_cart_item,
    create_cart,
    delete_cart_item,
    get_cart_item,
    get_cart_items_details,
    get_movie_by_id,
    get_purchased_movies_from_db,
    get_user_cart,
)
from database.session_postgresql import get_postgresql_db
from schemas.accounts import MessageResponseSchema
from schemas.shopping_cart import (
    CartCreate,
    CartItemResponse,
    CartResponse,
    PurchasedMoviesResponse,
)
from security.http import get_token
from validation.shopping_cart import (
    validate_movie_availability,
    validate_not_in_cart,
    validate_not_purchased,
)

router = APIRouter()


@router.get("/", response_model=CartResponse)
def get_cart(
        db: Session = Depends(get_postgresql_db),
        token: str = Depends(get_token),
        jwt_manager=Depends(get_jwt_auth_manager)
):
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    cart = get_user_cart(user, db)
    if not cart:
        return CartResponse(user_id=user.id, movies=[])
    return CartResponse(user_id=user.id, movies=get_cart_items_details(cart))


@router.post("/add", response_model=CartResponse)
def add_to_cart(
        cart_data: CartCreate,
        db: Session = Depends(get_postgresql_db),
        token: str = Depends(get_token),
        jwt_manager=Depends(get_jwt_auth_manager)
):
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    movie = get_movie_by_id(cart_data.movie_id, db)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    validate_movie_availability(movie)
    validate_not_purchased(user, movie, db)
    validate_not_in_cart(user, movie, db)

    cart = get_user_cart(user, db) or create_cart(user, db)
    add_cart_item(cart, movie, db)
    db.refresh(cart)

    return CartResponse(user_id=user.id, movies=get_cart_items_details(cart))


@router.delete("/remove/{movie_id}", response_model=CartItemResponse)
def remove_from_cart(
        movie_id: int,
        db: Session = Depends(get_postgresql_db),
        token: str = Depends(get_token),
        jwt_manager=Depends(get_jwt_auth_manager)
):
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    cart = get_user_cart(user, db)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    cart_item = get_cart_item(cart, movie_id, db)
    if not cart_item:
        raise HTTPException(status_code=404, detail="Movie not in cart")

    delete_cart_item(cart_item, db)
    return CartItemResponse(message="Movie removed from cart")


@router.delete("/clear", response_model=CartItemResponse)
def clear_cart(
        db: Session = Depends(get_postgresql_db),
        token: str = Depends(get_token),
        jwt_manager=Depends(get_jwt_auth_manager)
):
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    cart = get_user_cart(user, db)
    if not cart or not cart.items:
        raise HTTPException(status_code=404, detail="Cart is already empty")

    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()

    return CartItemResponse(message="Cart cleared successfully")


@router.post("/checkout", response_model=MessageResponseSchema)
def checkout(
        db: Session = Depends(get_postgresql_db),
        token: str = Depends(get_token),
        jwt_manager=Depends(get_jwt_auth_manager)
):
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Please activate your account before making a purchase."
        )

    cart = get_user_cart(user, db)
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Your cart is empty")

    order = Order(
        user_id=user.id,
        total_amount=sum(item.movie.price for item in cart.items)
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    order_items = []
    for item in cart.items:
        order_item = OrderItem(
            order_id=order.id,
            movie_id=item.movie.id,
            price_at_order=item.movie.price
        )
        db.add(order_item)
        order_items.append(order_item)

    db.commit()

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

    for order_item in order_items:
        payment_item = PaymentItem(
            payment_id=payment.id,
            order_item_id=order_item.id,
            price_at_payment=order_item.price_at_order
        )
        db.add(payment_item)

    db.commit()

    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()

    return MessageResponseSchema(message="Payment successful")


@router.get("/purchased", response_model=PurchasedMoviesResponse)
def get_purchased_movies(
        db: Session = Depends(get_postgresql_db),
        token: str = Depends(get_token),
        jwt_manager=Depends(get_jwt_auth_manager)
):
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    purchased_movies = get_purchased_movies_from_db(user, db)
    return PurchasedMoviesResponse(
        purchased_movies=[movie.name for movie in purchased_movies]
    )


@router.get("/admin/{user_id}", response_model=CartResponse)
def get_user_cart_admin(
        user_id: int,
        db: Session = Depends(get_postgresql_db),
        token: str = Depends(get_token),
        jwt_manager=Depends(get_jwt_auth_manager)
):
    try:
        payload = jwt_manager.decode_access_token(token)
        admin_id = payload.get("user_id")
        admin = db.query(User).filter(User.id == admin_id).first()

        if not admin or not admin.has_group(UserGroupEnum.ADMIN):
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    cart = get_user_cart(user, db)
    if not cart:
        return CartResponse(user_id=user.id, movies=[])

    return CartResponse(user_id=user.id, movies=get_cart_items_details(cart))


@router.delete(
    "/admin/movies/{movie_id}",
    response_model=MessageResponseSchema
)
def delete_movie(
        movie_id: int,
        db: Session = Depends(get_postgresql_db),
        token: str = Depends(get_token),
        jwt_manager=Depends(get_jwt_auth_manager)
):
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
        user = db.query(User).filter(User.id == user_id).first()

        if not user or not (
                user.has_group(UserGroupEnum.ADMIN)
                or user.has_group(UserGroupEnum.MODERATOR)
        ):
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    cart_items = (
        db.query(CartItem).filter(CartItem.movie_id == movie.id).count()
    )
    if cart_items > 0:
        raise HTTPException(
            status_code=400,
            detail="Movie cannot be deleted because it exists in user carts"
        )

    db.delete(movie)
    db.commit()
    return MessageResponseSchema(message="Movie deleted successfully")
