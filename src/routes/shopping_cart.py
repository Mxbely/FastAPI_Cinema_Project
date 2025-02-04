from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config import get_jwt_auth_manager
from database import (
    Order,
    User,
    UserGroupEnum,
)
from database.crud.accounts import get_user_by_id
from database.crud.shopping_cart import (
    add_cart_item,
    create_cart,
    create_order,
    delete_cart_item,
    delete_cart_item_by_cart,
    delete_movie,
    get_cart_item,
    get_cart_items_details,
    get_movie_by_id,
    get_purchased_movies_from_db,
    get_user_cart,
    is_movie_in_any_cart,
    process_order_payment_and_clear_cart,
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
from security.token_manager import JWTAuthManager
from validation.shopping_cart import (
    validate_movie_availability,
    validate_not_in_cart,
    validate_not_purchased,
)

router = APIRouter()


@router.get(
    "/",
    response_model=CartResponse,
    summary="Retrieve user's shopping cart",
    description=(
        "<h3>Fetch the user's shopping cart.</h3>"
        "Returns a list of movies currently in the user's shopping cart."
    ),
    responses={
        404: {"description": "User not found."},
        401: {"description": "Unauthorized request."}
    }
)
def get_cart(
        db: Annotated[Session, Depends(get_postgresql_db)],
        token: Annotated[str, Depends(get_token)],
        jwt_manager: Annotated[JWTAuthManager, Depends(get_jwt_auth_manager)]
) -> CartResponse:
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


@router.post(
    "/add",
    response_model=CartResponse,
    summary="Add a movie to the shopping cart",
    description=(
        "<h3>Add a movie to the user's shopping cart.</h3>"
        "Validates availability and ensures the movie is not already in the cart."
    ),
    responses={
        404: {"description": "User or movie not found."},
        400: {"description": "Movie already in cart."},
        401: {"description": "Unauthorized request."}
    }
)
def add_to_cart(
        cart_data: CartCreate,
        db: Annotated[Session, Depends(get_postgresql_db)],
        token: Annotated[str, Depends(get_token)],
        jwt_manager: Annotated[JWTAuthManager, Depends(get_jwt_auth_manager)]
) -> CartResponse:
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


@router.delete(
    "/remove/{movie_id}",
    response_model=CartItemResponse,
    summary="Remove a movie from the shopping cart",
    description=(
        "<h3>Removes a specific movie from the user's shopping cart.</h3>"
        "If the movie is not found in the cart, returns an error."
    ),
    responses={
        404: {"description": "Movie or cart not found."},
        401: {"description": "Unauthorized request."}
    }
)
def remove_from_cart(
        movie_id: int,
        db: Annotated[Session, Depends(get_postgresql_db)],
        token: Annotated[str, Depends(get_token)],
        jwt_manager: Annotated[JWTAuthManager, Depends(get_jwt_auth_manager)]
) -> CartItemResponse:
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    user = get_user_by_id(db, user_id)
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


@router.delete(
    "/clear",
    response_model=CartItemResponse,
    summary="Clear the shopping cart",
    description=(
        "<h3>Removes all movies from the shopping cart.</h3>"
        "If the cart is already empty, returns an error."
    ),
    responses={
        404: {"description": "Cart already empty."},
        401: {"description": "Unauthorized request."}
    }
)
def clear_cart(
        db: Annotated[Session, Depends(get_postgresql_db)],
        token: Annotated[str, Depends(get_token)],
        jwt_manager: Annotated[JWTAuthManager, Depends(get_jwt_auth_manager)]
) -> CartItemResponse:
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    cart = get_user_cart(user, db)
    if not cart or not cart.items:
        raise HTTPException(status_code=404, detail="Cart is already empty")

    delete_cart_item_by_cart(db, cart.id)

    return CartItemResponse(message="Cart cleared successfully")


@router.post(
    "/checkout",
    response_model=MessageResponseSchema,
    summary="Checkout and complete purchase",
    description=(
        "<h3>Processes the purchase of items in the shopping cart.</h3>"
        "Creates an order and clears the shopping cart."
    ),
    responses={
        404: {"description": "User not found."},
        403: {"description": "User not activated."},
        400: {"description": "Cart is empty."},
        401: {"description": "Unauthorized request."}
    }
)
def checkout(
        db: Annotated[Session, Depends(get_postgresql_db)],
        token: Annotated[str, Depends(get_token)],
        jwt_manager: Annotated[JWTAuthManager, Depends(get_jwt_auth_manager)]
) -> MessageResponseSchema:
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    user = get_user_by_id(db, user_id)
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
    create_order(db, order)

    process_order_payment_and_clear_cart(db, user, order, cart)

    return MessageResponseSchema(
        message="Order placed successfully. Payment has been created."
    )


@router.get(
    "/purchased",
    response_model=PurchasedMoviesResponse,
    summary="Retrieve purchased movies",
    description=(
        "<h3>Fetch a list of movies the user has purchased.</h3>"
        "Returns a list of movie names that the user has successfully bought."
    ),
    responses={
        404: {"description": "User not found."},
        401: {"description": "Unauthorized request."}
    }
)
def get_purchased_movies(
        db: Annotated[Session, Depends(get_postgresql_db)],
        token: Annotated[str, Depends(get_token)],
        jwt_manager: Annotated[JWTAuthManager, Depends(get_jwt_auth_manager)]
) -> PurchasedMoviesResponse:
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    purchased_movies = get_purchased_movies_from_db(user, db)
    return PurchasedMoviesResponse(
        purchased_movies=[movie.name for movie in purchased_movies]
    )


@router.get(
    "/admin/{user_id}",
    response_model=CartResponse,
    summary="Retrieve a user's cart as an admin",
    description=(
        "<h3>Allows an admin to view a specific user's shopping cart.</h3>"
        "Admin access is required."
    ),
    responses={
        404: {"description": "User or cart not found."},
        403: {"description": "Access denied."},
        401: {"description": "Unauthorized request."}
    }
)
def get_user_cart_admin(
        user_id: int,
        db: Annotated[Session, Depends(get_postgresql_db)],
        token: Annotated[str, Depends(get_token)],
        jwt_manager: Annotated[JWTAuthManager, Depends(get_jwt_auth_manager)]
) -> CartResponse:
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

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    cart = get_user_cart(user, db)
    if not cart:
        return CartResponse(user_id=user.id, movies=[])

    return CartResponse(user_id=user.id, movies=get_cart_items_details(cart))


@router.delete(
    "/admin/movies/{movie_id}",
    response_model=MessageResponseSchema,
    summary="Delete a movie from the system",
    description=(
        "<h3>Allows an admin or moderator to delete a movie from the system.</h3>"
        "If the movie is present in any user's cart, deletion is denied."
    ),
    responses={
        404: {"description": "Movie not found."},
        403: {"description": "Access denied."},
        400: {"description": "Movie is in user carts and cannot be deleted."},
        401: {"description": "Unauthorized request."}
    }
)
def delete_movie_route(
        movie_id: int,
        db: Annotated[Session, Depends(get_postgresql_db)],
        token: Annotated[str, Depends(get_token)],
        jwt_manager: Annotated[JWTAuthManager, Depends(get_jwt_auth_manager)]
) -> MessageResponseSchema:
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

    movie = get_movie_by_id(movie_id, db)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    if is_movie_in_any_cart(db, movie_id):
        raise HTTPException(
            status_code=400,
            detail="Movie cannot be deleted because it exists in user carts"
        )

    delete_movie(db, movie)
    return MessageResponseSchema(message="Movie deleted successfully")
