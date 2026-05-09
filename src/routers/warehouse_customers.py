from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
import uuid
from sqlalchemy import select, or_, func
import json
import base64
from datetime import datetime

from ..database.database import get_db
from ..models.user import User
from ..models.warehouse_customer import WarehouseCustomer, WarehouseCustomerCreate, WarehouseCustomerUpdate, WarehouseCustomerRead
from ..services.warehouse_customer_service import WarehouseCustomerService
from ..auth.session_auth import admin_required_from_session, admin_employee_warehouse_required_from_session

router = APIRouter()

@router.get("/", response_model=List[WarehouseCustomerRead])
async def get_customers(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Get list of warehouse customers with pagination"""
    return await WarehouseCustomerService.get_customers(db, skip=skip, limit=limit)

@router.get("/viewcustomer")
async def view_customers(
    search_string: str = None,
    branches: str = None,
    page: int = 1,
    limit: int = 10000,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """View warehouse customers with search and branch filtering"""
    skip = (page - 1) * limit
    base_statement = select(WarehouseCustomer)

    if branches:
        base_statement = base_statement.where(WarehouseCustomer.branch == branches)

    if search_string and search_string.strip():
        search_pattern = f"%{search_string.strip()}%"
        base_statement = base_statement.where(
            or_(
                WarehouseCustomer.name.ilike(search_pattern),
                WarehouseCustomer.contacts.ilike(search_pattern),
                WarehouseCustomer.cnic.ilike(search_pattern)
            )
        )

    count_statement = select(func.count()).select_from(base_statement.subquery())
    count_result = await db.execute(count_statement)
    total_count = count_result.scalar() or 0

    statement = base_statement.offset(skip).limit(limit)
    result = await db.execute(statement)
    customers = result.scalars().all()

    result_list = []
    for customer in customers:
        contacts_data = {}
        try:
            contacts_data = json.loads(customer.contacts)
        except:
            contacts_data = {"phone": "", "email": "", "address": ""}

        customer_data = {
            "cus_id": str(customer.id),
            "cus_name": customer.name,
            "cus_phone": contacts_data.get("phone", ""),
            "cus_cnic": customer.cnic or "",
            "cus_address": contacts_data.get("address", ""),
            "branch": customer.branch or "",
            "cus_balance": float(customer.cus_balance or 0.0)
        }
        result_list.append(customer_data)

    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    return {
        'data': result_list,
        'page': page,
        'limit': limit,
        'total': total_count,
        'totalPages': total_pages
    }

@router.post("/", response_model=WarehouseCustomerRead)
async def create_customer(
    customer_create: WarehouseCustomerCreate,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Create a new warehouse customer"""
    return await WarehouseCustomerService.create_customer(db, customer_create, str(current_user.id))

@router.get("/market-balance")
async def get_market_balance(
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the total balance due from all warehouse customers (Total Market Balance)
    """
    statement = select(func.sum(WarehouseCustomer.cus_balance))
    result = await db.execute(statement)
    total_market_balance = float(result.scalar() or 0.0)
    
    return {"total_market_balance": total_market_balance}

@router.get("/{customer_id}", response_model=WarehouseCustomerRead)
async def get_customer(
    customer_id: str,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific warehouse customer by ID"""
    try:
        customer_uuid = UUID(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid customer ID format")

    customer = await WarehouseCustomerService.get_customer(db, customer_uuid)
    if not customer:
        raise HTTPException(status_code=404, detail="Warehouse customer not found")
    return customer

@router.put("/{customer_id}", response_model=WarehouseCustomerRead)
async def update_customer(
    customer_id: str,
    customer_update: WarehouseCustomerUpdate,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Update a specific warehouse customer by ID"""
    try:
        customer_uuid = UUID(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid customer ID format")

    customer = await WarehouseCustomerService.update_customer(db, customer_uuid, customer_update, str(current_user.id))
    if not customer:
        raise HTTPException(status_code=404, detail="Warehouse customer not found")
    return customer

@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: str,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Delete a specific warehouse customer by ID"""
    try:
        customer_uuid = UUID(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid customer ID format")

    success = await WarehouseCustomerService.delete_customer(db, customer_uuid, str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="Warehouse customer not found")
    return {"message": "Warehouse customer deleted successfully"}

@router.post("/customerviewreport")
async def customer_view_report(
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Generate warehouse customer view report PDF"""
    customers = await WarehouseCustomerService.get_customers(db, skip=0, limit=10000)
    
    total_market_balance = sum(float(c.cus_balance or 0.0) for c in customers)

    customer_rows = ""
    for i, customer in enumerate(customers):
        contacts_data = {}
        try:
            contacts_data = json.loads(customer.contacts)
        except:
            contacts_data = {"phone": "", "email": "", "address": ""}

        customer_rows += f"""
        <tr>
            <td class="border" style="text-align: center;">{i+1}</td>
            <td class="border">{customer.name}</td>
            <td class="border">{contacts_data.get('phone', '')}</td>
            <td class="border">{contacts_data.get('address', '')}</td>
            <td class="border">{customer.branch or ''}</td>
            <td class="border text-right">{float(customer.cus_balance or 0.0):.2f}</td>
        </tr>
        """
    
    customer_rows += f"""
        <tr class="total-row">
            <td class="border" colspan="5" style="text-align: right; font-weight: bold;">Total Balance:</td>
            <td class="border text-right" style="font-weight: bold;">{total_market_balance:.2f}</td>
        </tr>
    """
    
    current_date = datetime.now().strftime('%d-%m-%Y')
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4 landscape; margin: 15mm; }}
            body {{ font-family: Arial, sans-serif; font-size: 15px; }}
            h1 {{ text-align: center; font-weight: bold; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th {{ background-color: #444; color: white; border: 1px solid #000; padding: 10px; }}
            td {{ border: 1px solid #000; padding: 10px; }}
            .text-right {{ text-align: right; }}
            .total-row {{ background-color: #e0e0e0; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>Warehouse Customer Details</h1>
        <div style="text-align: right;"><strong>Print Date:</strong> {current_date}</div>
        <table>
            <thead>
                <tr>
                    <th style="width: 50px;">#</th>
                    <th>Customer Name</th>
                    <th>Phone</th>
                    <th>Address</th>
                    <th>Branch</th>
                    <th style="width: 120px; text-align: right;">Balance</th>
                </tr>
            </thead>
            <tbody>
                {customer_rows}
            </tbody>
        </table>
    </body>
    </html>
    """
    
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        return base64.b64encode(pdf_bytes).decode()
    except:
        return base64.b64encode(b"PDF Generation Error").decode()
