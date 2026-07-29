from flask import Blueprint, render_template, request, flash, redirect, url_for
from app import db, limiter
from app.models import DeleteRequest, DeleteAttachment
from app.utils.upload import save_upload
from app.utils.captcha import generate_captcha, verify_captcha
from app.utils.notify import notify_admin_telegram

contact_bp = Blueprint("contact", __name__)


@contact_bp.route("/contact", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def delete_request():
    captcha_q, captcha_token = generate_captcha()

    if request.method == "POST":
        if not verify_captcha(request.form.get("captcha_answer", ""), request.form.get("captcha_token", "")):
            flash("الإجابة على سؤال التحقق غير صحيحة", "error")
            captcha_q, captcha_token = generate_captcha()
            return render_template("contact.html", captcha_q=captcha_q, captcha_token=captcha_token)

        full_name = request.form.get("full_name", "").strip()
        contact = request.form.get("contact", "").strip()
        imei_or_sn = request.form.get("imei_or_sn", "").strip()
        reason = request.form.get("reason", "").strip()

        errors = []
        if not full_name:
            errors.append("الاسم الكامل مطلوب")
        if not contact:
            errors.append("البريد أو رقم الهاتف مطلوب")
        if not imei_or_sn:
            errors.append("رقم IMEI أو التسلسلي مطلوب")
        if not reason:
            errors.append("سبب طلب الحذف مطلوب")

        if errors:
            for e in errors:
                flash(e, "error")
            captcha_q, captcha_token = generate_captcha()
            return render_template("contact.html", captcha_q=captcha_q, captcha_token=captcha_token)

        req = DeleteRequest(
            full_name=full_name,
            contact=contact,
            imei_or_sn=imei_or_sn,
            reason=reason,
            status="pending",
        )
        db.session.add(req)
        db.session.flush()

        for key in ("proof_file1", "proof_file2"):
            if key in request.files:
                stored, original = save_upload(request.files[key], prefix="del")
                if stored:
                    att = DeleteAttachment(
                        request_id=req.id,
                        filename=stored,
                        original_name=original,
                    )
                    db.session.add(att)

        # Extra files
        for f in request.files.getlist("extra_files"):
            stored, original = save_upload(f, prefix="delx")
            if stored:
                db.session.add(DeleteAttachment(
                    request_id=req.id, filename=stored, original_name=original
                ))

        db.session.commit()
        notify_admin_telegram(f"طلب حذف بلاغ:\n{imei_or_sn}\nمن: {full_name}")

        flash("تم إرسال طلب الحذف بنجاح. سيتم مراجعته قريبًا.", "success")
        return redirect(url_for("contact.delete_request"))

    return render_template("contact.html", captcha_q=captcha_q, captcha_token=captcha_token)
