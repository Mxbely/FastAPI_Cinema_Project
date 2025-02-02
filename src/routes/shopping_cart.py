from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)
from sqlalchemy.orm import Session

from database.session_postgresql import get_postgresql_db
from schemas.shopping_cart import (
    CartCreate,
    CartResponse,
    CartItemResponse,
    CartItemDetail
)
from database.models.accounts import User
from database.crud.shopping_cart import (
    get_user_cart,
    get_movie_by_id,
    get_cart_item,
    create_cart,
    add_cart_item,
    delete_cart_item
)
from validation.shopping_cart import (
    validate_not_in_cart,
    validate_not_purchased,
    validate_movie_availability
)


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

    cart = get_user_cart(user, db)
    if not cart:
        cart = create_cart(user, db)

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

    delete_cart_item(cart_item, db)
    return CartItemResponse(message="Movie removed from cart")


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
