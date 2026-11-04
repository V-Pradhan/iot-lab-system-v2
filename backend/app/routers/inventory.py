import csv
import io
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..logic import audit
from ..models import Equipment, InventoryLog, Lab
from ..security import STAFF, get_lab, require_roles

router = APIRouter(prefix="/api")
LABELS = {"name": "name", "category": "category", "total_qty": "total", "damaged_qty": "damaged",
          "missing_qty": "missing", "maintenance_qty": "maintenance", "notes": "notes"}


def eq_dict(e: Equipment) -> dict:
    return {"id": e.id, "name": e.name, "category": e.category, "total_qty": e.total_qty,
            "available_qty": e.available_qty, "issued_qty": e.issued_qty,
            "damaged_qty": e.damaged_qty, "missing_qty": e.missing_qty,
            "maintenance_qty": e.maintenance_qty, "notes": e.notes}


class EquipmentIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category: str = Field(default="", max_length=60)
    total_qty: int = Field(ge=0, le=100000)
    damaged_qty: int = Field(default=0, ge=0)
    missing_qty: int = Field(default=0, ge=0)
    maintenance_qty: int = Field(default=0, ge=0)
    notes: str = Field(default="", max_length=255)
    reason: str = Field(default="", max_length=200)


class EquipmentPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    category: Optional[str] = Field(default=None, max_length=60)
    total_qty: Optional[int] = Field(default=None, ge=0, le=100000)
    damaged_qty: Optional[int] = Field(default=None, ge=0)
    missing_qty: Optional[int] = Field(default=None, ge=0)
    maintenance_qty: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=255)
    reason: str = Field(default="", max_length=200)


def _rebalance(e: Equipment):
    avail = e.total_qty - e.issued_qty - e.damaged_qty - e.missing_qty - e.maintenance_qty
    if avail < 0:
        raise HTTPException(400, f"Quantities exceed the total. {e.issued_qty} unit(s) are currently issued.")
    e.available_qty = avail


@router.get("/inventory")
def list_inventory(q: str = "", db: Session = Depends(get_db), lab: Lab = Depends(get_lab), _=Depends(require_roles(*STAFF))):
    query = db.query(Equipment).filter(Equipment.lab_id == lab.id)
    if q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(Equipment.name.ilike(like) | Equipment.category.ilike(like))
    return [eq_dict(e) for e in query.order_by(Equipment.name).all()]


@router.post("/inventory", status_code=201)
def create_equipment(data: EquipmentIn, db: Session = Depends(get_db), lab: Lab = Depends(get_lab),
                     user=Depends(require_roles(*STAFF))):
    name = data.name.strip()
    if db.query(Equipment).filter(Equipment.lab_id == lab.id, Equipment.name == name).first():
        raise HTTPException(409, "Equipment with this name already exists in this laboratory")
    e = Equipment(lab_id=lab.id, name=name, category=data.category.strip(), total_qty=data.total_qty, issued_qty=0,
                  damaged_qty=data.damaged_qty, missing_qty=data.missing_qty,
                  maintenance_qty=data.maintenance_qty, notes=data.notes)
    _rebalance(e)
    db.add(e)
    db.flush()
    db.add(InventoryLog(lab_id=lab.id, equipment_id=e.id, equipment_name=e.name, user_id=user.id, action="add",
                        change=f"added with total {e.total_qty}", reason=data.reason.strip()))
    audit(db, user, "add_equipment", f"{e.name} x{e.total_qty} ({lab.name})")
    db.commit()
    return eq_dict(e)


@router.get("/inventory/log")
def inventory_log(db: Session = Depends(get_db), lab: Lab = Depends(get_lab), _=Depends(require_roles(*STAFF))):
    rows = db.query(InventoryLog).filter(InventoryLog.lab_id == lab.id).order_by(InventoryLog.id.desc()).limit(100).all()
    return [{"id": r.id, "at": r.created_at.isoformat(), "user": r.user.full_name if r.user else "",
             "equipment": r.equipment_name, "action": r.action, "change": r.change, "reason": r.reason} for r in rows]


@router.patch("/inventory/{eid}")
def update_equipment(eid: int, data: EquipmentPatch, db: Session = Depends(get_db), lab: Lab = Depends(get_lab),
                     user=Depends(require_roles(*STAFF))):
    e = db.query(Equipment).filter(Equipment.id == eid, Equipment.lab_id == lab.id).with_for_update().first()
    if not e:
        raise HTTPException(404, "Equipment not found in this laboratory")
    changes = []
    for f, label in LABELS.items():
        v = getattr(data, f)
        if v is None:
            continue
        v = v.strip() if isinstance(v, str) else v
        old = getattr(e, f)
        if v != old:
            if f == "name" and db.query(Equipment).filter(Equipment.lab_id == lab.id, Equipment.name == v, Equipment.id != e.id).first():
                raise HTTPException(409, "Another item in this laboratory already has that name")
            changes.append(f"{label} {old} \u2192 {v}")
            setattr(e, f, v)
    _rebalance(e)
    if changes:
        db.add(InventoryLog(lab_id=lab.id, equipment_id=e.id, equipment_name=e.name, user_id=user.id, action="update",
                            change="; ".join(changes)[:400], reason=data.reason.strip()))
        audit(db, user, "update_equipment", f"{e.name}: {'; '.join(changes)} ({lab.name})")
    db.commit()
    return eq_dict(e)


# --------------------------------------------------------------- CSV import
ALIASES = {
    "name": {"name", "item", "item name", "equipment", "equipment name", "component"},
    "category": {"category", "type", "group"},
    "total_qty": {"total", "total_qty", "total qty", "total quantity", "quantity", "qty", "count"},
    "damaged_qty": {"damaged", "damaged_qty", "damaged qty"},
    "missing_qty": {"missing", "missing_qty", "missing qty", "lost"},
    "maintenance_qty": {"maintenance", "maintenance_qty", "maintenance qty", "in maintenance", "repair"},
    "notes": {"notes", "note", "remarks", "remark", "description"},
}
MAX_ROWS = 2000


class ImportIn(BaseModel):
    csv: str = Field(max_length=800_000)
    mode: Literal["add_update", "add_only"] = "add_update"
    dry_run: bool = True
    filename: str = Field(default="", max_length=100)


def _to_int(text: str, label: str) -> Optional[int]:
    text = (text or "").strip()
    if text == "":
        return None
    try:
        f = float(text.replace(",", ""))
    except ValueError:
        raise ValueError(f"{label} must be a whole number (found \"{text}\")")
    if f != int(f):
        raise ValueError(f"{label} must be a whole number (found \"{text}\")")
    n = int(f)
    if n < 0 or n > 100000:
        raise ValueError(f"{label} must be between 0 and 100000")
    return n


@router.post("/inventory/import")
def import_inventory(data: ImportIn, db: Session = Depends(get_db), lab: Lab = Depends(get_lab),
                     user=Depends(require_roles(*STAFF))):
    """Add or update many items from a CSV file. A dry run only checks and previews. Nothing is saved if any row has an error."""
    text = data.csv.lstrip("\ufeff")
    if not text.strip():
        raise HTTPException(400, "The file is empty")
    try:
        dialect = csv.Sniffer().sniff(text[:2000], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    rows = list(reader)
    header = [h.strip().lower() for h in rows[0]]
    col = {}
    for field, names in ALIASES.items():
        for i, h in enumerate(header):
            if h in names and field not in col:
                col[field] = i
    if "name" not in col or "total_qty" not in col:
        raise HTTPException(400, "The first row must be a header with at least the columns: name, total "
                                 "(optional: category, damaged, missing, maintenance, notes)")
    body = [(n, r) for n, r in enumerate(rows[1:], start=2) if any(c.strip() for c in r)]
    if len(body) > MAX_ROWS:
        raise HTTPException(400, f"Too many rows (limit {MAX_ROWS} per file)")

    existing = {e.name.lower(): e for e in
                db.query(Equipment).filter(Equipment.lab_id == lab.id).with_for_update().all()}
    seen, errors, plan = set(), [], []
    for line, r in body:
        def cell(f):
            i = col.get(f)
            return r[i] if i is not None and i < len(r) else ""
        try:
            name = cell("name").strip()
            if len(name) < 2 or len(name) > 120:
                raise ValueError("name must be 2 to 120 characters")
            if name.lower() in seen:
                raise ValueError(f"\"{name}\" appears twice in the file")
            seen.add(name.lower())
            vals = {f: _to_int(cell(f), f.replace("_qty", "")) for f in ("total_qty", "damaged_qty", "missing_qty", "maintenance_qty")}
            category, notes = cell("category").strip()[:60], cell("notes").strip()[:255]
            cur = existing.get(name.lower())
            if cur is None:
                if vals["total_qty"] is None:
                    raise ValueError("total is needed for a new item")
                new = Equipment(lab_id=lab.id, name=name, category=category, notes=notes, issued_qty=0,
                                total_qty=vals["total_qty"], damaged_qty=vals["damaged_qty"] or 0,
                                missing_qty=vals["missing_qty"] or 0, maintenance_qty=vals["maintenance_qty"] or 0)
                _rebalance(new)
                plan.append({"line": line, "name": name, "action": "add", "total": new.total_qty, "obj": new, "changes": []})
            elif data.mode == "add_only":
                plan.append({"line": line, "name": cur.name, "action": "skip", "total": cur.total_qty, "obj": None, "changes": []})
            else:
                changes, sets = [], {}
                for f, label in (("total_qty", "total"), ("damaged_qty", "damaged"), ("missing_qty", "missing"), ("maintenance_qty", "maintenance")):
                    if vals[f] is not None and vals[f] != getattr(cur, f):
                        changes.append(f"{label} {getattr(cur, f)} \u2192 {vals[f]}")
                        sets[f] = vals[f]
                if "category" in col and category and category != cur.category:
                    changes.append(f"category {cur.category} \u2192 {category}"); sets["category"] = category
                if "notes" in col and notes and notes != cur.notes:
                    changes.append("notes changed"); sets["notes"] = notes
                probe = Equipment(**{c.name: getattr(cur, c.name) for c in Equipment.__table__.columns if c.name != "id"})
                for k, v in sets.items():
                    setattr(probe, k, v)
                _rebalance(probe)           # raises if the new quantities do not fit the units already issued
                plan.append({"line": line, "name": cur.name, "action": "update" if changes else "unchanged",
                             "total": probe.total_qty, "obj": cur, "changes": changes, "sets": sets})
        except HTTPException as e:
            errors.append({"line": line, "message": f"{e.detail}"})
        except ValueError as e:
            errors.append({"line": line, "message": str(e)})

    count = lambda a: sum(1 for p in plan if p["action"] == a)
    result = {"applied": False, "created": count("add"), "updated": count("update"), "unchanged": count("unchanged"),
              "skipped": count("skip"), "errors": errors[:100], "error_count": len(errors),
              "preview": [{"line": p["line"], "name": p["name"], "action": p["action"], "total": p["total"],
                           "changes": "; ".join(p["changes"])} for p in plan[:200]]}
    if data.dry_run or errors:
        return result

    reason = f"CSV import {data.filename}".strip()[:200]
    for p in plan:
        if p["action"] == "add":
            db.add(p["obj"])
            db.flush()
            db.add(InventoryLog(lab_id=lab.id, equipment_id=p["obj"].id, equipment_name=p["name"], user_id=user.id,
                                action="add", change=f"added with total {p['total']}", reason=reason))
        elif p["action"] == "update":
            for k, v in p["sets"].items():
                setattr(p["obj"], k, v)
            _rebalance(p["obj"])
            db.add(InventoryLog(lab_id=lab.id, equipment_id=p["obj"].id, equipment_name=p["name"], user_id=user.id,
                                action="update", change="; ".join(p["changes"])[:400], reason=reason))
    audit(db, user, "import_inventory", f"{data.filename}: {result['created']} added, {result['updated']} updated ({lab.name})")
    db.commit()
    result["applied"] = True
    return result
