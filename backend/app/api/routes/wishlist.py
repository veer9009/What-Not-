from fastapi import APIRouter, Request
from pydantic import StrictBool
from app.api.dependencies import Buyer, TransactionSession
from app.api.contracts import IdentifierPath
from app.schemas.common import ContractModel
from app.services.wishlist import WishlistService
router=APIRouter(prefix='/wishlist',tags=['Wishlist'])
class SavedInput(ContractModel):saved:StrictBool
@router.get('')
def listing(user:Buyer,session:TransactionSession,request:Request):return WishlistService(session,request.app.state.settings).list(user.id)
@router.put('/{product_id}')
def save(product_id:IdentifierPath,data:SavedInput,user:Buyer,session:TransactionSession):return WishlistService(session).put(user.id,product_id,data.saved)
