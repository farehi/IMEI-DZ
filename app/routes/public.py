from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from sqlalchemy import or_, func
from app import db, limiter
from app.models import Report, ReportAttachment, SearchLog
from app.utils.imei import is_valid_imei, normalize_imei, generate_reference
from app.utils.upload import save_upload
from app.utils.crypto import encrypt_text, decrypt_text
from app.utils.captcha import generate_captcha, verify_captcha
from app.utils.notify import notify_admin_telegram

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def index():
    total = Report.query.filter(Report.deleted_at.is_(None), Report.status == "approved").count()
    searches = db.session.query(SearchLog).count()
    return render_template("index.html", total_reports=total, total_searches=searches)


@public_bp.route("/check", methods=["GET", "POST"])
@limiter.limit("30 per minute")
def check_phone():
    result = None
    query = ""

    if request.method == "POST":
        query = normalize_imei(request.form.get("imei", ""))
        if not query:
            flash("يرجى إدخال رقم IMEI أو الرقم التسلسلي", "error")
            return render_template("check.html", result=None, query="")

        report = (
            Report.query.filter(
                Report.deleted_at.is_(None),
                Report.status == "approved",
                or_(
                    Report.imei1 == query,
                    Report.imei2 == query,
                    Report.serial_number == query,
                ),
            ).first()
        )

        found = report is not None
        result = {"found": found, "report": report, "query": query}

        log = SearchLog(
            query=query,
            result="found" if found else "not_found",
            ip_address=request.remote_addr,
        )
        db.session.add(log)
        db.session.commit()

    return render_template("check.html", result=result, query=query)


@public_bp.route("/report", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def report_stolen():
    captcha_q, captcha_token = generate_captcha()

    if request.method == "POST":
        # CAPTCHA
        if not verify_captcha(request.form.get("captcha_answer", ""), request.form.get("captcha_token", "")):
            flash("الإجابة على سؤال التحقق غير صحيحة", "error")
            captcha_q, captcha_token = generate_captcha()
            return render_template("report.html", captcha_q=captcha_q, captcha_token=captcha_token)

        imei1 = normalize_imei(request.form.get("imei1", ""))
        imei2 = normalize_imei(request.form.get("imei2", "")) or None
        serial = normalize_imei(request.form.get("serial_number", "")) or None

        brand = request.form.get("brand", "").strip()
        model = request.form.get("model", "").strip()
        color = request.form.get("color", "").strip() or None
        theft_date = request.form.get("theft_date", "").strip() or None
        theft_location = request.form.get("theft_location", "").strip() or None
        owner_name = request.form.get("owner_name", "").strip()
        owner_phone = request.form.get("owner_phone", "").strip()
        incident_details = request.form.get("incident_details", "").strip() or None

        errors = []
        if not is_valid_imei(imei1):
            errors.append("رقم IMEI 1 غير صالح (15 رقمًا + خوارزمية Luhn)")
        if imei2 and not is_valid_imei(imei2):
            errors.append("رقم IMEI 2 غير صالح")
        if not brand:
            errors.append("الشركة المصنعة مطلوبة")
        if not model:
            errors.append("الموديل مطلوب")
        if not owner_name:
            errors.append("اسم المالك مطلوب")
        if not owner_phone:
            errors.append("رقم هاتف التواصل مطلوب")

        conditions = [Report.imei1 == imei1]
        if imei1:
            conditions.append(Report.imei2 == imei1)
        if imei2:
            conditions.append(Report.imei1 == imei2)
            conditions.append(Report.imei2 == imei2)

        existing = (
            Report.query.filter(
                Report.deleted_at.is_(None),
                Report.status.in_(["pending", "approved"]),
                or_(*conditions),
            ).first()
        )
        if existing:
            errors.append(f"يوجد بلاغ سابق لهذا الجهاز: {existing.reference}")

        if errors:
            for e in errors:
                flash(e, "error")
            captcha_q, captcha_token = generate_captcha()
            return render_template("report.html", captcha_q=captcha_q, captcha_token=captcha_token)

        year = datetime.utcnow().year
        last = (
            Report.query.filter(Report.reference.like(f"DZ-{year}-%"))
            .order_by(Report.id.desc())
            .first()
        )
        seq = 1
        if last and last.reference:
            try:
                seq = int(last.reference.split("-")[-1]) + 1
            except ValueError:
                seq = 1
        reference = generate_reference(year, seq)

        report = Report(
            reference=reference,
            imei1=imei1,
            imei2=imei2,
            serial_number=serial,
            brand=brand,
            model=model,
            color=color,
            theft_date=theft_date,
            theft_location=theft_location,
            owner_name_enc=encrypt_text(owner_name),
            owner_phone_enc=encrypt_text(owner_phone),
            incident_details=incident_details,
            status="pending",
        )
        db.session.add(report)
        db.session.flush()

        # Multiple files
        files = request.files.getlist("ownership_files")
        for f in files:
            stored, original = save_upload(f, prefix="own")
            if stored:
                att = ReportAttachment(
                    report_id=report.id,
                    filename=stored,
                    original_name=original,
                    file_type=stored.rsplit(".", 1)[-1] if "." in stored else None,
                )
                db.session.add(att)

        db.session.commit()

        notify_admin_telegram(f"بلاغ جديد: {reference}\n{brand} {model}\nIMEI: {imei1}")

        flash(f"تم إرسال البلاغ بنجاح. الرقم المرجعي: {reference}", "success")
        return redirect(url_for("public.report_success", ref=reference))

    return render_template("report.html", captcha_q=captcha_q, captcha_token=captcha_token)


@public_bp.route("/report/success/<ref>")
def report_success(ref):
    report = Report.query.filter_by(reference=ref).first_or_404()
    return render_template("report_success.html", report=report)


@public_bp.route("/track", methods=["GET", "POST"])
@limiter.limit("20 per minute")
def track_report():
    """Owner tracks report status by reference number."""
    report = None
    ref = ""

    if request.method == "POST":
        ref = request.form.get("reference", "").strip().upper()
        if ref:
            report = Report.query.filter_by(reference=ref).filter(Report.deleted_at.is_(None)).first()
            if not report:
                flash("لم يتم العثور على بلاغ بهذا الرقم المرجعي", "error")
    elif request.args.get("ref"):
        ref = request.args.get("ref", "").strip().upper()
        report = Report.query.filter_by(reference=ref).filter(Report.deleted_at.is_(None)).first()

    return render_template("track.html", report=report, ref=ref)


@public_bp.route("/report/<ref>")
def report_public_detail(ref):
    """Public detail page (limited info for approved reports)."""
    report = (
        Report.query.filter_by(reference=ref, status="approved")
        .filter(Report.deleted_at.is_(None))
        .first_or_404()
    )
    return render_template("report_detail_public.html", report=report)


@public_bp.route("/api/check/<imei>")
@limiter.limit("60 per minute")
def api_check(imei):
    query = normalize_imei(imei)
    if not query:
        return jsonify({"error": "invalid input"}), 400

    report = (
        Report.query.filter(
            Report.deleted_at.is_(None),
            Report.status == "approved",
            or_(
                Report.imei1 == query,
                Report.imei2 == query,
                Report.serial_number == query,
            ),
        ).first()
    )

    if report:
        return jsonify({
            "status": "stolen",
            "reference": report.reference,
            "brand": report.brand,
            "model": report.model,
            "reported_at": report.created_at.isoformat() if report.created_at else None,
        })
    return jsonify({"status": "clean"})
