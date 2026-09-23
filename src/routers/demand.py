from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta

from ..database.database import get_db
from ..models.user import User
from ..models.demand import Demand, DemandCreate
from ..models.demand_item import DemandItem
from ..auth.session_auth import employee_required_from_session, get_current_user_from_session

router = APIRouter()


@router.post("/create")
async def create_demand(
    demand_data: DemandCreate,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Record a customer demand for an article not currently available in the shop."""
    if not demand_data.demand_text or not demand_data.demand_text.strip():
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Demand text is required"
        )

    if not demand_data.category or not demand_data.category.strip():
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Category is required"
        )

    demand_text = demand_data.demand_text.strip()

    # If the client didn't send a demand_item_id (e.g. free text typed
    # without picking a suggestion), still link it when the text exactly
    # matches an existing item - otherwise it silently fragments the
    # Top Items ranking / report into a duplicate "unlinked" group.
    demand_item_id = demand_data.demand_item_id
    if not demand_item_id:
        match = await db.execute(
            select(DemandItem.id).where(func.lower(DemandItem.name) == demand_text.lower())
        )
        demand_item_id = match.scalar_one_or_none()

    demand = Demand(
        demand_text=demand_text,
        demand_item_id=demand_item_id,
        category=demand_data.category.strip(),
        customer_name=demand_data.customer_name.strip() if demand_data.customer_name else None,
        customer_phone=demand_data.customer_phone.strip() if demand_data.customer_phone else None,
        created_by=current_user.id,
    )
    db.add(demand)
    await db.commit()
    await db.refresh(demand)

    return {
        "success": True,
        "id": str(demand.id),
        "message": "Demand recorded successfully"
    }


@router.get("/list")
async def get_demands(
    search_string: Optional[str] = None,
    page: int = 1,
    limit: int = 8,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """List recorded demands with optional search filtering."""
    if page < 1:
        page = 1
    if limit <= 0 or limit > 100:
        limit = 8
    skip = (page - 1) * limit

    conditions = []
    if search_string and search_string.strip():
        pattern = f"%{search_string.strip()}%"
        conditions.append(or_(
            Demand.demand_text.ilike(pattern),
            Demand.customer_name.ilike(pattern),
            Demand.customer_phone.ilike(pattern),
            Demand.category.ilike(pattern),
        ))

    count_statement = select(func.count(Demand.id))
    statement = select(Demand)
    for condition in conditions:
        count_statement = count_statement.where(condition)
        statement = statement.where(condition)

    count_result = await db.execute(count_statement)
    total_count = count_result.scalar() or 0

    statement = statement.order_by(Demand.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(statement)
    demands = result.scalars().all()

    data = [
        {
            "id": str(demand.id),
            "demand_text": demand.demand_text,
            "category": demand.category or "",
            "customer_name": demand.customer_name or "",
            "customer_phone": demand.customer_phone or "",
            "created_at": demand.created_at.isoformat(),
        }
        for demand in demands
    ]

    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    return {
        "data": data,
        "page": page,
        "limit": limit,
        "total": total_count,
        "total_pages": total_pages,
        "has_more": page < total_pages,
    }


MAX_COMPARE_ITEMS = 8  # matches the fixed 8-slot categorical palette on the frontend
DEFAULT_TOP_N = 5  # how many articles the default (no selection) graph charts


@router.get("/stats")
async def get_demand_stats(
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD, defaults to 30 days ago"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD, defaults to today"),
    demand_item_id: Optional[UUID] = None,
    demand_item_ids: Optional[str] = Query(None, description="Comma-separated demand_item ids to compare on one chart"),
    category: Optional[str] = None,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Demand volume over a date range: a most-demanded-items ranking, and a
    per-article daily trend for either an explicit selection
    (demand_item_id / demand_item_ids, up to MAX_COMPARE_ITEMS) or, with no
    selection, the top 8 ranked items. Powers the graph + date picker on /demand.
    """
    today = datetime.now().date()
    try:
        first_day = datetime.fromisoformat(from_date).date() if from_date else today - timedelta(days=29)
        last_day = datetime.fromisoformat(to_date).date() if to_date else today
    except ValueError:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD")
    if first_day > last_day:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="from_date must be before or equal to to_date")

    range_conditions = [
        func.date(Demand.created_at) >= first_day,
        func.date(Demand.created_at) <= last_day,
    ]
    if category:
        range_conditions.append(Demand.category == category)

    # ---- Which items to chart: an explicit selection (one or more), or the top 8 ----
    selected_ids: list[UUID] = []
    if demand_item_ids:
        for raw in demand_item_ids.split(","):
            raw = raw.strip()
            if not raw:
                continue
            try:
                selected_ids.append(UUID(raw))
            except ValueError:
                raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Invalid demand_item_ids value: {raw}")
    elif demand_item_id:
        selected_ids = [demand_item_id]
    selected_ids = selected_ids[:MAX_COMPARE_ITEMS]

    # ---- Top demanded items (only demands linked to a catalog item) ----
    # No limit - the frontend list scrolls, every article demanded in range shows.
    top_statement = (
        select(
            DemandItem.id,
            DemandItem.name,
            DemandItem.category,
            func.count(Demand.id).label("demand_count"),
        )
        .join(Demand, Demand.demand_item_id == DemandItem.id)
        .where(and_(*range_conditions))
        .group_by(DemandItem.id)
        .order_by(func.count(Demand.id).desc())
    )
    top_result = await db.execute(top_statement)
    top_items = [
        {
            "id": str(row.id),
            "name": row.name,
            "category": row.category or "",
            "count": row.demand_count,
        }
        for row in top_result.all()
    ]

    # ---- Resolve which items the chart actually draws: the explicit
    # selection (looked up directly, so a selected article with zero demand
    # in-range still charts as a flat line) or, absent one, the top 8 ----
    if selected_ids:
        info_statement = select(DemandItem.id, DemandItem.name, DemandItem.category).where(DemandItem.id.in_(selected_ids))
        info_result = await db.execute(info_statement)
        info_by_id = {str(row.id): {"name": row.name, "category": row.category or ""} for row in info_result.all()}
        chart_item_ids = [i for i in selected_ids if str(i) in info_by_id]
    else:
        chart_item_ids = [UUID(item["id"]) for item in top_items[:DEFAULT_TOP_N]]
        info_by_id = {item["id"]: {"name": item["name"], "category": item["category"]} for item in top_items[:DEFAULT_TOP_N]}

    # ---- Per-item daily trend, zero-filled for every day in range ----
    series = []
    if chart_item_ids:
        multi_statement = (
            select(
                func.date(Demand.created_at).label("date"),
                Demand.demand_item_id.label("item_id"),
                func.count(Demand.id).label("count"),
            )
            .where(and_(*range_conditions, Demand.demand_item_id.in_(chart_item_ids)))
            .group_by(func.date(Demand.created_at), Demand.demand_item_id)
        )
        multi_result = await db.execute(multi_statement)
        per_item_daily_counts: dict = {}
        for row in multi_result.all():
            per_item_daily_counts.setdefault(str(row.item_id), {})[row.date] = row.count

        date_cursor = []
        current_date = first_day
        while current_date <= last_day:
            date_cursor.append(current_date)
            current_date += timedelta(days=1)

        for item_id in chart_item_ids:
            key = str(item_id)
            info = info_by_id.get(key, {"name": "Unknown", "category": ""})
            item_daily = per_item_daily_counts.get(key, {})
            series.append({
                "id": key,
                "name": info["name"],
                "counts": [item_daily.get(d, 0) for d in date_cursor],
            })

    dates = [
        (first_day + timedelta(days=n)).strftime("%Y-%m-%d")
        for n in range((last_day - first_day).days + 1)
    ]

    return {
        "topItems": top_items,
        "seriesChartData": {"dates": dates, "series": series},
        "dateRange": {"from": first_day.strftime("%Y-%m-%d"), "to": last_day.strftime("%Y-%m-%d")},
    }


async def _fetch_ranked_demand_groups(db: AsyncSession, from_date, to_date, category):
    """
    Shared by the PDF/Excel reports: groups demand records by article (linked
    catalog item when there is one, otherwise the raw text) instead of just
    date order, so the report answers "what should I restock" and "who do I
    call back" without the reader having to filter/pivot it themselves.
    """
    conditions = []
    if from_date:
        conditions.append(func.date(Demand.created_at) >= datetime.fromisoformat(from_date).date())
    if to_date:
        conditions.append(func.date(Demand.created_at) <= datetime.fromisoformat(to_date).date())
    if category:
        conditions.append(Demand.category == category)

    statement = (
        select(Demand, DemandItem.name, DemandItem.category)
        .outerjoin(DemandItem, Demand.demand_item_id == DemandItem.id)
        .order_by(Demand.created_at.desc())
    )
    if conditions:
        statement = statement.where(and_(*conditions))
    result = await db.execute(statement)
    rows = result.all()

    groups: dict = {}
    order = []
    for demand, item_name, item_category in rows:
        key = str(demand.demand_item_id) if demand.demand_item_id else f"text::{(demand.demand_text or '').strip().lower()}"
        if key not in groups:
            groups[key] = {
                "name": item_name or demand.demand_text,
                "category": item_category or demand.category or "",
                "count": 0,
                "entries": [],
            }
            order.append(key)
        groups[key]["count"] += 1
        groups[key]["entries"].append({
            "customer_name": demand.customer_name or "",
            "customer_phone": demand.customer_phone or "",
            "created_at": demand.created_at,
        })

    ranked = sorted(groups.values(), key=lambda g: g["count"], reverse=True)
    return len(rows), ranked


@router.get("/list/pdf")
async def get_demand_list_pdf(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    category: Optional[str] = None,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Printable PDF report: a ranked "what to restock" summary, followed by a
    per-article customer follow-up list (grouped, not just chronological).
    """
    total_count, ranked_groups = await _fetch_ranked_demand_groups(db, from_date, to_date, category)

    summary_rows_html = "".join(
        f"""
        <tr>
          <td>{i + 1}</td>
          <td>{g['name']}</td>
          <td>{g['category'] or '-'}</td>
          <td class="num">{g['count']}</td>
        </tr>"""
        for i, g in enumerate(ranked_groups)
    )

    detail_sections_html = "".join(
        f"""
        <div class="article-block">
          <h3>{g['name']} <span class="tag">{g['category'] or 'Uncategorized'}</span> <span class="count">{g['count']}x demanded</span></h3>
          <table>
            <thead><tr><th>Customer</th><th>Phone</th><th>Date</th></tr></thead>
            <tbody>
              {''.join(f"<tr><td>{e['customer_name'] or '-'}</td><td>{e['customer_phone'] or '-'}</td><td>{e['created_at'].strftime('%d-%m-%Y')}</td></tr>" for e in g['entries'])}
            </tbody>
          </table>
        </div>"""
        for g in ranked_groups
    )

    range_label = f"{from_date or 'All'} to {to_date or 'Today'}"
    html_content = f"""
    <html>
    <head><style>
      body {{ font-family: Arial, sans-serif; font-size: 12px; color: #171717; }}
      h1 {{ font-size: 18px; margin-bottom: 2px; }}
      h2 {{ font-size: 14px; margin: 22px 0 4px; }}
      h3 {{ font-size: 12.5px; margin: 14px 0 4px; }}
      p.sub {{ color: #666; margin-top: 0; }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 6px; }}
      th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: left; }}
      th {{ background: #FFD700; color: #000; text-transform: uppercase; font-size: 10px; }}
      td.num {{ text-align: center; font-weight: bold; }}
      .tag {{ font-weight: normal; color: #666; font-size: 11px; }}
      .count {{ font-weight: normal; color: #0f9d8e; font-size: 11px; }}
      .article-block {{ page-break-inside: avoid; }}
    </style></head>
    <body>
      <h1>Demand Report</h1>
      <p class="sub">{range_label} &middot; {total_count} demands across {len(ranked_groups)} articles</p>

      <h2>Most Demanded Articles - what to restock first</h2>
      <table>
        <thead><tr><th>Rank</th><th>Article</th><th>Category</th><th>Times Demanded</th></tr></thead>
        <tbody>{summary_rows_html}</tbody>
      </table>

      <h2>Customer Follow-up List - who to call when it's back in stock</h2>
      {detail_sections_html}
    </body>
    </html>
    """

    import base64
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        encoded_pdf = base64.b64encode(pdf_bytes).decode()
    except Exception:
        pdf_content = "%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] >>\nendobj\nxref\n0 4\ntrailer\n<< /Size 4 /Root 1 0 R >>\n%%EOF"
        encoded_pdf = base64.b64encode(pdf_content.encode()).decode()

    return {"pdf": encoded_pdf}


@router.get("/list/excel")
async def get_demand_list_excel(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    category: Optional[str] = None,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Excel report: a "Summary" sheet ranked by demand count (restock
    decisions), and a "Follow-up List" sheet grouped by article with each
    customer who asked for it (still fully filterable/sortable in Excel).
    """
    total_count, ranked_groups = await _fetch_ranked_demand_groups(db, from_date, to_date, category)
    range_label = f"{from_date or 'All'} to {to_date or 'Today'}"

    import io
    import base64
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill

    wb = Workbook()

    title_font = Font(bold=True, size=14)
    subtitle_font = Font(color="666666", size=10, italic=True)
    header_font = Font(bold=True, color="000000")
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")
    group_font = Font(bold=True, color="FFFFFF")
    group_fill = PatternFill(start_color="0F9D8E", end_color="0F9D8E", fill_type="solid")
    subhead_font = Font(bold=True, size=10)
    subhead_fill = PatternFill(start_color="F3F4F6", end_color="F3F4F6", fill_type="solid")
    center = Alignment(horizontal="center", vertical="center")
    thin = Side(style="thin", color="000000")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    def write_title_block(ws, last_col_letter):
        ws.merge_cells(f"A1:{last_col_letter}1")
        ws["A1"] = "Demand Report"
        ws["A1"].font = title_font
        ws["A1"].alignment = center
        ws["A1"].border = border
        ws.merge_cells(f"A2:{last_col_letter}2")
        ws["A2"] = f"{range_label}  |  {total_count} demands across {len(ranked_groups)} articles"
        ws["A2"].font = subtitle_font
        ws["A2"].alignment = center
        ws["A2"].border = border

    # ---- Summary sheet: ranked "what to restock" table ----
    ws1 = wb.active
    ws1.title = "Summary"
    write_title_block(ws1, "D")

    summary_headers = ["Rank", "Article", "Category", "Times Demanded"]
    for col, header in enumerate(summary_headers, start=1):
        cell = ws1.cell(row=4, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = border
    for i, g in enumerate(ranked_groups, start=5):
        row_values = [i - 4, g["name"], g["category"], g["count"]]
        for col, value in enumerate(row_values, start=1):
            cell = ws1.cell(row=i, column=col, value=value)
            cell.border = border
            cell.alignment = center
    for col, width in zip("ABCD", [8, 34, 18, 16]):
        ws1.column_dimensions[col].width = width

    # ---- Follow-up List sheet: grouped per article (bold group header +
    # its customers below it), like the PDF's article blocks ----
    ws2 = wb.create_sheet("Follow-up List")
    write_title_block(ws2, "C")

    row = 4
    for g in ranked_groups:
        ws2.merge_cells(f"A{row}:C{row}")
        group_cell = ws2.cell(row=row, column=1, value=f"{g['name']}  -  {g['category'] or 'Uncategorized'}  -  {g['count']}x demanded")
        group_cell.font = group_font
        group_cell.fill = group_fill
        group_cell.alignment = center
        group_cell.border = border
        for col in range(2, 4):
            side_cell = ws2.cell(row=row, column=col)
            side_cell.fill = group_fill
            side_cell.border = border
        row += 1

        for col, header in enumerate(["Customer", "Phone", "Date"], start=1):
            cell = ws2.cell(row=row, column=col, value=header)
            cell.font = subhead_font
            cell.fill = subhead_fill
            cell.alignment = center
            cell.border = border
        row += 1

        for e in g["entries"]:
            values = [e["customer_name"] or "-", e["customer_phone"] or "-", e["created_at"].strftime("%d-%m-%Y")]
            for col, value in enumerate(values, start=1):
                cell = ws2.cell(row=row, column=col, value=value)
                cell.border = border
                cell.alignment = center
            row += 1

        row += 1  # spacer row between article blocks

    for col, width in zip("ABC", [30, 18, 14]):
        ws2.column_dimensions[col].width = width

    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    encoded_excel = base64.b64encode(excel_buffer.read()).decode()

    filename = f"Demand_Report_{from_date or 'all'}_to_{to_date or 'today'}.xlsx"
    return {"excel": encoded_excel, "filename": filename}


@router.put("/update/{demand_id}")
async def update_demand(
    demand_id: str,
    request_data: dict,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Edit a demand's details (text, category, customer)."""
    try:
        demand_uuid = UUID(demand_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid demand ID format"
        )

    result = await db.execute(select(Demand).where(Demand.id == demand_uuid))
    demand = result.scalar_one_or_none()
    if not demand:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Demand not found"
        )

    if "demand_text" in request_data:
        new_text = (request_data.get("demand_text") or "").strip()
        if not new_text:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Demand text cannot be empty"
            )
        demand.demand_text = new_text

    if "category" in request_data:
        new_category = (request_data.get("category") or "").strip()
        if not new_category:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Category is required"
            )
        demand.category = new_category

    if "customer_name" in request_data:
        value = (request_data.get("customer_name") or "").strip()
        demand.customer_name = value or None

    if "customer_phone" in request_data:
        value = (request_data.get("customer_phone") or "").strip()
        demand.customer_phone = value or None

    demand.updated_at = datetime.now()
    await db.commit()
    await db.refresh(demand)

    return {
        "success": True,
        "id": str(demand.id),
        "demand_text": demand.demand_text,
        "category": demand.category or "",
        "customer_name": demand.customer_name or "",
        "customer_phone": demand.customer_phone or "",
    }


@router.delete("/{demand_id}")
async def delete_demand(
    demand_id: str,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """Delete a demand record. Restricted to admin for accountability."""
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Only admin can delete demand records"
        )

    try:
        demand_uuid = UUID(demand_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid demand ID format"
        )

    result = await db.execute(select(Demand).where(Demand.id == demand_uuid))
    demand = result.scalar_one_or_none()
    if not demand:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Demand not found"
        )

    await db.delete(demand)
    await db.commit()

    return {"success": True, "message": "Demand deleted successfully"}
