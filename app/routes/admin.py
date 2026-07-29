from datetime import datetime, timedelta
from io import BytesIO
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session, send_file, abort
)
from sqlalchemy import or_, func
from app import db
from app.models import (
    Report, DeleteRequest, AuditLog, SearchLog, FailedLogin, AdminUser, ReportAttachment
)
from app.utils.auth import login_required, role_required, check_admin_credentials, hash_password
from app.utils.crypto import decrypt_text
from app.utils.notify import notify_report_status, notify_admin_telegram

admin_bp = Blueprint("admin", __name__)


def log_action(action, entity_type=None, entity_id=None, details=None):
    entry = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        admin_user=session.get("admin_user"),
        ip_address=request.remote_addr,
    )
    db.session.add(entry)
    db.session.commit()


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        ok, role = check_admin_credentials(username, password)
        if ok:
            session["admin_logged_in"] = True
            session["admin_user"] = username
            session["admin_role"] = role
            # update last_login if in DB
            user = AdminUser.query.filter_by(username=username).first()
            if user:
                user.last_login = datetime.utcnow()
                db.session.commit()
            log_action("login")
            return redirect(url_for("admin.dashboard"))

        # Failed login log
        fl = FailedLogin(
            username=username,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:250],
        )
        db.session.add(fl)
        db.session.commit()
        flash("بيانات الدخول غير صحيحة", "error")

    return render_template("admin/login.html")


@admin_bp.route("/logout")
@login_required
def logout():
    log_action("logout")
    session.clear()
    return redirect(url_for("admin.login"))


@admin_bp.route("/")
@login_required
def dashboard():
    total = Report.query.filter(Report.deleted_at.is_(None)).count()
    pending = Report.query.filter_by(status="pending").filter(Report.deleted_at.is_(None)).count()
    approved = Report.query.filter_by(status="approved").filter(Report.deleted_at.is_(None)).count()
    rejected = Report.query.filter_by(status="rejected").filter(Report.deleted_at.is_(None)).count()
    delete_reqs = DeleteRequest.query.filter_by(status="pending").count()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    searches_today = SearchLog.query.filter(SearchLog.created_at >= today_start).count()
    failed_logins_today = FailedLogin.query.filter(FailedLogin.created_at >= today_start).count()

    # Chart data: last 7 days reports
    chart_labels = []
    chart_counts = []
    for i in range(6, -1, -1):
        day = today_start - timedelta(days=i)
        day_end = day + timedelta(days=1)
        cnt = Report.query.filter(
            Report.created_at >= day,
            Report.created_at < day_end,
            Report.deleted_at.is_(None),
        ).count()
        chart_labels.append(day.strftime("%m-%d"))
        chart_counts.append(cnt)

    # By wilaya (theft_location)
    by_location = (
        db.session.query(Report.theft_location, func.count(Report.id))
        .filter(Report.deleted_at.is_(None), Report.theft_location.isnot(None), Report.theft_location != "")
        .group_by(Report.theft_location)
        .order_by(func.count(Report.id).desc())
        .limit(10)
        .all()
    )

    recent = (
        Report.query.filter(Report.deleted_at.is_(None))
        .order_by(Report.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        total=total,
        pending=pending,
        approved=approved,
        rejected=rejected,
        delete_reqs=delete_reqs,
        searches_today=searches_today,
        failed_logins_today=failed_logins_today,
        chart_labels=chart_labels,
        chart_counts=chart_counts,
        by_location=by_location,
        recent=recent,
    )


@admin_bp.route("/reports")
@login_required
def reports():
    status = request.args.get("status", "all")
    q = request.args.get("q", "").strip()
    brand = request.args.get("brand", "").strip()
    location = request.args.get("location", "").strip()

    query = Report.query.filter(Report.deleted_at.is_(None))

    if status != "all":
        query = query.filter_by(status=status)
    if q:
        query = query.filter(
            or_(
                Report.reference.ilike(f"%{q}%"),
                Report.imei1.ilike(f"%{q}%"),
                Report.imei2.ilike(f"%{q}%"),
                Report.brand.ilike(f"%{q}%"),
                Report.model.ilike(f"%{q}%"),
            )
        )
    if brand:
        query = query.filter(Report.brand.ilike(f"%{brand}%"))
    if location:
        query = query.filter(Report.theft_location.ilike(f"%{location}%"))

    reports_list = query.order_by(Report.created_at.desc()).limit(200).all()
    return render_template(
        "admin/reports.html",
        reports=reports_list,
        status=status,
        q=q,
        brand=brand,
        location=location,
    )


@admin_bp.route("/reports/<int:report_id>", methods=["GET", "POST"])
@login_required
def report_detail(report_id):
    report = Report.query.get_or_404(report_id)

    if request.method == "POST":
        if session.get("admin_role") == "viewer":
            flash("ليس لديك صلاحية التعديل", "error")
            return redirect(url_for("admin.report_detail", report_id=report.id))

        action = request.form.get("action")
        notes = request.form.get("admin_notes", "").strip()

        if action == "approve":
            report.status = "approved"
            report.admin_notes = notes
            log_action("approve_report", "report", report.id, notes)
            phone = decrypt_text(report.owner_phone_enc)
            notify_report_status(phone, report.reference, "approved")
            flash("تم قبول البلاغ", "success")
        elif action == "reject":
            report.status = "rejected"
            report.admin_notes = notes
            log_action("reject_report", "report", report.id, notes)
            phone = decrypt_text(report.owner_phone_enc)
            notify_report_status(phone, report.reference, "rejected")
            flash("تم رفض البلاغ", "success")
        elif action == "delete":
            report.deleted_at = datetime.utcnow()
            report.status = "deleted"
            log_action("soft_delete_report", "report", report.id, notes)
            flash("تم حذف البلاغ (منطقيًا)", "success")
        elif action == "update_notes":
            report.admin_notes = notes
            log_action("update_notes", "report", report.id, notes)
            flash("تم تحديث الملاحظات", "success")

        db.session.commit()
        return redirect(url_for("admin.report_detail", report_id=report.id))

    owner_name = decrypt_text(report.owner_name_enc)
    owner_phone = decrypt_text(report.owner_phone_enc)
    attachments = report.attachments.all()

    return render_template(
        "admin/report_detail.html",
        report=report,
        owner_name=owner_name,
        owner_phone=owner_phone,
        attachments=attachments,
    )


@admin_bp.route("/delete-requests")
@login_required
def delete_requests():
    status = request.args.get("status", "pending")
    reqs = DeleteRequest.query.filter_by(status=status).order_by(DeleteRequest.created_at.desc()).all()
    return render_template("admin/delete_requests.html", requests=reqs, status=status)


@admin_bp.route("/delete-requests/<int:req_id>", methods=["POST"])
@role_required("superadmin", "moderator")
def process_delete_request(req_id):
    req = DeleteRequest.query.get_or_404(req_id)
    action = request.form.get("action")
    notes = request.form.get("admin_notes", "").strip()

    if action == "approve":
        reports = Report.query.filter(
            Report.deleted_at.is_(None),
            or_(
                Report.imei1 == req.imei_or_sn,
                Report.imei2 == req.imei_or_sn,
                Report.serial_number == req.imei_or_sn,
                Report.reference == req.imei_or_sn,
            ),
        ).all()
        for r in reports:
            r.deleted_at = datetime.utcnow()
            r.status = "deleted"
            log_action("delete_via_request", "report", r.id, f"via delete_request {req.id}")

        req.status = "approved"
        req.admin_notes = notes
        req.processed_at = datetime.utcnow()
        log_action("approve_delete_request", "delete_request", req.id, notes)
        flash("تم قبول طلب الحذف", "success")

    elif action == "reject":
        req.status = "rejected"
        req.admin_notes = notes
        req.processed_at = datetime.utcnow()
        log_action("reject_delete_request", "delete_request", req.id, notes)
        flash("تم رفض طلب الحذف", "success")

    db.session.commit()
    return redirect(url_for("admin.delete_requests"))


@admin_bp.route("/audit")
@login_required
def audit():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(150).all()
    return render_template("admin/audit.html", logs=logs)


@admin_bp.route("/failed-logins")
@role_required("superadmin")
def failed_logins():
    logs = FailedLogin.query.order_by(FailedLogin.created_at.desc()).limit(100).all()
    return render_template("admin/failed_logins.html", logs=logs)


@admin_bp.route("/export")
@role_required("superadmin", "moderator")
def export_reports():
    """Export reports as CSV (Excel-compatible)."""
    import csv
    status = request.args.get("status", "all")
    query = Report.query.filter(Report.deleted_at.is_(None))
    if status != "all":
        query = query.filter_by(status=status)
    rows = query.order_by(Report.created_at.desc()).all()

    output = BytesIO()
    # Write BOM for Excel Arabic
    output.write(b"\xef\xbb\xbf")
    # csv needs text wrapper
    from io import TextIOWrapper
    text = TextIOWrapper(output, encoding="utf-8", newline="")
    writer = csv.writer(text)
    writer.writerow([
        "reference", "imei1", "imei2", "serial", "brand", "model",
        "color", "theft_date", "theft_location", "status", "created_at"
    ])
    for r in rows:
        writer.writerow([
            r.reference, r.imei1, r.imei2 or "", r.serial_number or "",
            r.brand, r.model, r.color or "", r.theft_date or "",
            r.theft_location or "", r.status,
            r.created_at.isoformat() if r.created_at else "",
        ])
    text.flush()
    output.seek(0)
    text.detach()

    log_action("export_reports", details=f"status={status} count={len(rows)}")
    return send_file(
        output,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"reports_{datetime.utcnow().strftime('%Y%m%d')}.csv",
    )


@admin_bp.route("/users", methods=["GET", "POST"])
@role_required("superadmin")
def manage_users():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            role = request.form.get("role", "moderator")
            if username and password and role in ("superadmin", "moderator", "viewer"):
                if AdminUser.query.filter_by(username=username).first():
                    flash("اسم المستخدم موجود", "error")
                else:
                    u = AdminUser(
                        username=username,
                        password_hash=hash_password(password),
                        role=role,
                    )
                    db.session.add(u)
                    db.session.commit()
                    log_action("create_admin", "admin_user", u.id, role)
                    flash("تم إنشاء المستخدم", "success")
        elif action == "toggle":
            uid = request.form.get("user_id")
            u = AdminUser.query.get(uid)
            if u and u.username != session.get("admin_user"):
                u.is_active = not u.is_active
                db.session.commit()
                log_action("toggle_admin", "admin_user", u.id)
                flash("تم التحديث", "success")
        return redirect(url_for("admin.manage_users"))

    users = AdminUser.query.order_by(AdminUser.created_at.desc()).all()
    return render_template("admin/users.html", users=users)
