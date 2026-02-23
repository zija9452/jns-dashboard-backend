from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
import uuid
import json

from ..database.database import get_db
from ..models.user import User
from ..models.salesman import Salesman, SalesmanCreate, SalesmanUpdate, SalesmanRead
from ..services.salesman_service import SalesmanService
from ..auth.session_auth import get_current_user_from_session, admin_required_from_session, cashier_required_from_session, employee_required_from_session, admin_cashier_employee_required_from_session

router = APIRouter()

@router.get("/", response_model=List[SalesmanRead])
async def get_salesmen(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(employee_required_from_session()),  # Employees and above can view salesmen
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of salesmen with pagination
    Employees and admins can view salesmen
    """
    salesmen = await SalesmanService.get_salesmen(db, skip=skip, limit=limit)
    return salesmen

@router.post("/", response_model=SalesmanRead)
async def create_salesman(
    salesman_create: SalesmanCreate,
    current_user: User = Depends(admin_required_from_session()),  # Only admins can create salesmen
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new salesman
    Requires admin role
    """
    return await SalesmanService.create_salesman(db, salesman_create, str(current_user.id))

# Frontend-compatible endpoints (MUST be before /{salesman_id} routes)

@router.get("/viewsalesman")
async def view_salesmen(
    search_string: Optional[str] = None,
    branches: Optional[str] = None,
    searchphone: Optional[str] = None,
    page: int = 1,
    limit: int = 8,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    View salesmen with search and branch filtering
    Required by JavaScript frontend - matches customer/vendor pattern
    Returns: Paginated data + total count for proper frontend pagination
    """
    # Calculate skip from page
    skip = (page - 1) * limit

    # Build base query
    base_statement = select(Salesman)

    # Apply branch filter at database level
    if branches:
        base_statement = base_statement.where(Salesman.branch == branches)

    # Apply search filters at database level
    if search_string and search_string.strip():
        search_pattern = f"%{search_string.strip()}%"
        base_statement = base_statement.where(Salesman.name.ilike(search_pattern))

    # Get total count
    count_statement = select(Salesman.id)
    if branches:
        count_statement = count_statement.where(Salesman.branch == branches)
    if search_string and search_string.strip():
        search_pattern = f"%{search_string.strip()}%"
        count_statement = count_statement.where(Salesman.name.ilike(search_pattern))

    count_result = await db.execute(count_statement)
    total_count = len(count_result.scalars().all())

    # Apply pagination at database level
    statement = base_statement.offset(skip).limit(limit)

    # Execute query
    result = await db.execute(statement)
    salesmen = result.scalars().all()

    # Format the response to match expected frontend structure
    result_list = []
    for salesman in salesmen:
        result_list.append({
            "sal_id": str(salesman.id),
            "sal_name": salesman.name,
            "sal_phone": salesman.phone or '',
            "sal_address": salesman.address or '',
            "branch": salesman.branch or ''
        })

    # Calculate total pages
    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    # Prepare response with pagination info
    response_data = {
        'data': result_list,
        'page': page,
        'limit': limit,
        'total': total_count,
        'totalPages': total_pages
    }

    return response_data

@router.get("/{salesman_id}", response_model=SalesmanRead)
async def get_salesman(
    salesman_id: str,
    current_user: User = Depends(employee_required_from_session()),  # Employees and above can view salesman details
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific salesman by ID
    Employees and admins can view salesman details
    """
    try:
        salesman_uuid = UUID(salesman_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid salesman ID format"
        )

    salesman = await SalesmanService.get_salesman(db, salesman_uuid)

    if not salesman:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salesman not found"
        )

    return salesman

@router.put("/{salesman_id}", response_model=SalesmanRead)
async def update_salesman(
    salesman_id: str,
    salesman_update: SalesmanUpdate,
    current_user: User = Depends(admin_required_from_session()),  # Only admins can update salesmen
    db: AsyncSession = Depends(get_db)
):
    """
    Update a specific salesman by ID
    Requires admin role
    """
    try:
        salesman_uuid = UUID(salesman_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid salesman ID format"
        )

    salesman = await SalesmanService.get_salesman(db, salesman_uuid)

    if not salesman:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salesman not found"
        )

    return await SalesmanService.update_salesman(db, salesman_uuid, salesman_update, str(current_user.id))

@router.delete("/{salesman_id}")
async def delete_salesman(
    salesman_id: str,
    current_user: User = Depends(admin_required_from_session()),  # Only admins can delete salesmen
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific salesman by ID
    Requires admin role
    """
    try:
        salesman_uuid = UUID(salesman_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid salesman ID format"
        )

    success = await SalesmanService.delete_salesman(db, salesman_uuid, str(current_user.id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salesman not found"
        )

    return {"message": "Salesman deleted successfully"}

# Helper function for filtering salesmen
async def _view_salesmen_impl(
    salesmen,
    search_string: str = None,
    branches: str = None,
    searchphone: str = None
):
    """Helper function to filter salesmen"""
    # Apply filters
    filtered_salesmen = []
    for salesman in salesmen:
        # Apply branch filter if provided
        if branches:
            salesman_branch = getattr(salesman, 'branch', '')
            if salesman_branch != branches:
                continue

        # Apply search filters
        should_include = True
        if search_string:
            search_lower = search_string.lower()
            if search_lower not in salesman.name.lower():
                should_include = False

        if should_include and searchphone:
            if searchphone not in (salesman.phone or ''):
                should_include = False

        if should_include:
            filtered_salesmen.append(salesman)

    # Format the response to match expected frontend structure (same as customers/vendors)
    result = []
    for salesman in filtered_salesmen:
        result.append({
            "sal_id": str(salesman.id),
            "sal_name": salesman.name,
            "sal_phone": salesman.phone or '',
            "sal_address": salesman.address or '',
            "branch": salesman.branch or ''
        })

    return result

@router.post("/salesmanviewreport")
async def salesman_view_report(
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate salesman view report with proper table format
    Required by JavaScript frontend - matches customer/vendor report
    """
    import base64
    from datetime import datetime
    
    # Fetch all salesmen
    salesmen = await SalesmanService.get_salesmen(db, skip=0, limit=100)
    
    # Build salesman rows for PDF table
    salesman_rows = ""
    for i, salesman in enumerate(salesmen):
        salesman_rows += f"""
        <tr>
            <td class="border" style="text-align: center;">{i+1}</td>
            <td class="border">{salesman.name}</td>
            <td class="border">{salesman.phone or ''}</td>
            <td class="border">{salesman.address or ''}</td>
            <td class="border">{salesman.branch or ''}</td>
        </tr>
        """
    
    # Create HTML content for PDF with proper table styling
    current_date = datetime.now().strftime('%d-%m-%Y')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: A4 landscape;
                margin: 15mm;
            }}
            body {{
                font-family: Arial, sans-serif;
                font-size: 15px;
                margin: 0;
                padding: 0;
            }}
            h1 {{
                text-align: center;
                color: #333;
                margin: 0 0 10px 0;
                font-size: 28px;
                font-weight: bold;
            }}
            .print-date {{
                text-align: right;
                margin-bottom: 15px;
                color: #666;
                font-size: 13px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            th {{
                background-color: #444;
                color: white;
                border: 2px solid #000;
                padding: 14px 12px;
                text-align: left;
                font-weight: bold;
                font-size: 16px;
            }}
            td {{
                border: 1px solid #000;
                padding: 12px;
                font-size: 15px;
            }}
            .border {{
                border: 1px solid #000;
            }}
            .text-right {{
                text-align: right;
            }}
            tr:nth-child(even) {{
                background-color: #f5f5f5;
            }}
            tr:nth-child(odd) {{
                background-color: #fff;
            }}
            .total-row {{
                background-color: #e0e0e0 !important;
                font-weight: bold;
                font-size: 16px;
            }}
            .footer {{
                margin-top: 20px;
                text-align: center;
                font-size: 13px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <h1>Salesman Details</h1>
        <div class="print-date"><strong>Print Date:</strong> {current_date}</div>
        <table>
            <thead>
                <tr>
                    <th style="width: 50px;">#</th>
                    <th>Salesman Name</th>
                    <th>Phone</th>
                    <th>Address</th>
                    <th>Branch</th>
                </tr>
            </thead>
            <tbody>
                {salesman_rows}
            </tbody>
        </table>
        <div class="footer">
            <p>Total Salesmen: {len(salesmen)}</p>
        </div>
    </body>
    </html>
    """
    
    # Generate PDF using weasyprint
    try:
        from weasyprint import HTML
        from io import BytesIO
        
        pdf_doc = HTML(string=html_content)
        pdf_bytes = pdf_doc.write_pdf()
        encoded_pdf = base64.b64encode(pdf_bytes).decode()
        
    except ImportError:
        # Fallback to simple PDF
        pdf_content = "%PDF-1.4\n"
        pdf_content += "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        pdf_content += "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        pdf_content += "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 792 612] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        pdf_content += "4 0 obj\n<< /Length 300 >>\nstream\n"
        pdf_content += "BT\n/F1 18 Tf 350 550 Td (Salesman Details) Tj ET\n"
        pdf_content += "ET\nendstream\nendobj\n"
        pdf_content += "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        pdf_content += "xref\n0 6\ntrailer\n<< /Size 6 /Root 1 0 R >>\n%%EOF"
        
        encoded_pdf = base64.b64encode(pdf_content.encode()).decode()
    
    return encoded_pdf