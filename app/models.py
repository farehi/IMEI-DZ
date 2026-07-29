from datetime import datetime
from app import db


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(20), unique=True, nullable=False, index=True)

    imei1 = db.Column(db.String(15), nullable=False, index=True)
    imei2 = db.Column(db.String(15), nullable=True, index=True)
    serial_number = db.Column(db.String(50), nullable=True, index=True)

    brand = db.Column(db.String(50), nullable=False, index=True)
    model = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(50), nullable=True)
    theft_date = db.Column(db.String(20), nullable=True)
    theft_location = db.Column(db.String(150), nullable=True, index=True)

    # Encrypted fields
    owner_name_enc = db.Column(db.Text, nullable=False)
    owner_phone_enc = db.Column(db.Text, nullable=False)
    incident_details = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), default="pending", index=True)
    admin_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    attachments = db.relationship(
        "ReportAttachment", backref="report", lazy="dynamic", cascade="all, delete-orphan"
    )

    def is_active(self):
        return self.status == "approved" and self.deleted_at is None

    def __repr__(self):
        return f"<Report {self.reference}>"


class ReportAttachment(db.Model):
    __tablename__ = "report_attachments"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("reports.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=True)
    file_type = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SearchLog(db.Model):
    __tablename__ = "search_logs"

    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(50), nullable=False, index=True)
    result = db.Column(db.String(20), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(50), nullable=False, index=True)
    entity_type = db.Column(db.String(30), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    admin_user = db.Column(db.String(50), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class FailedLogin(db.Model):
    __tablename__ = "failed_logins"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True, index=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class DeleteRequest(db.Model):
    __tablename__ = "delete_requests"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100), nullable=False)
    imei_or_sn = db.Column(db.String(50), nullable=False, index=True)
    reason = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(20), default="pending", index=True)
    admin_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)

    attachments = db.relationship(
        "DeleteAttachment", backref="delete_request", lazy="dynamic", cascade="all, delete-orphan"
    )


class DeleteAttachment(db.Model):
    __tablename__ = "delete_attachments"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("delete_requests.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AdminUser(db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="moderator")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
