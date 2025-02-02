from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import CartItem, Cart, User
from database.session_postgresql import get_postgresql_db
from schemas.shopping_cart import (
    CartCreate,
    CartResponse,
    CartItemResponse,
    CartItemDetail
)
from database.crud.shopping_cart import (
    get_user_cart,
    get_movie_by_id,
    get_cart_item,
    create_cart,
    add_cart_item,
    delete_cart_item,
    get_purchased_movies
)
from validation.shopping_cart import (
    validate_not_in_cart,
    validate_not_purchased,
    validate_movie_availability
)
from security import get_current_user

router = APIRouter(prefix="/cart", tags=["Shopping Cart"])


@router.get("/", response_model=CartResponse)
def get_cart(
        db: Session = Depends(get_postgresql_db),
        user: User = Depends(get_current_user)
):
    cart = get_user_cart(user, db)
    if not cart:
        return CartResponse(user_id=user.id, movies=[])
    return CartResponse(user_id=user.id, movies=get_cart_items_details(cart))


@router.post("/add", response_model=CartResponse)
def add_to_cart(
        cart_data: CartCreate,
        db: Session = Depends(get_postgresql_db),
        user: User = Depends(get_current_user)
):
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
        user: User = Depends(get_current_user)
):
    cart = get_user_cart(user, db)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    cart_item = get_cart_item(cart, movie_id, db)
    if not cart_item:
        raise HTTPException(status_code=404, detail="Movie not in cart")

    # notify_moderators(f"User {user.id} removed movie {cart_item.movie.name} from the cart.")
    delete_cart_item(cart_item, db)
    return CartItemResponse(message="Movie removed from cart")


@router.delete("/clear", response_model=CartItemResponse)
def clear_cart(
        db: Session = Depends(get_postgresql_db), user: User = Depends(get_current_user)
):
    cart = get_user_cart(user, db)
    if not cart or not cart.items:
        raise HTTPException(status_code=404, detail="Cart is already empty")

    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()

    return CartItemResponse(message="Cart cleared successfully")


@router.get("/purchased")
def get_purchased_movies(
        db: Session = Depends(get_postgresql_db),
        user: User = Depends(get_current_user)
):
    purchased_movies = get_purchased_movies(user, db)

    return {"purchased_movies": [movie.name for movie in purchased_movies]}


@router.get("/admin/carts")
def get_all_carts(
        db: Session = Depends(get_postgresql_db),
        user: User = Depends(get_current_user)
):
    if user.group.name != "moderator":
        raise HTTPException(status_code=403, detail="You are not authorized")

    all_carts = db.query(Cart).all()
    return {
        "carts": [
            {
                "user_id": cart.user_id,
                "movies": [item.movie.name for item in cart.items]
            }
            for cart in all_carts
        ]
    }


def get_cart_items_details(cart):
    return [
        CartItemDetail(
            movie_id=item.movie.id,
            title=item.movie.name,
            price=item.movie.price,
            genre=(
                item.movie.genres[0].name if item.movie.genres else "Unknown"
            ),
            release_year=item.movie.year
        )
        for item in cart.items
    ] if cart else []
