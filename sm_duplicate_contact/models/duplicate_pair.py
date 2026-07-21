# -*- coding: utf-8 -*-
from odoo import api, fields, models


class DuplicateContactPair(models.Model):
    _name = "duplicate.contact.pair"
    _description = "Duplicate Contact Pair"
    _order = "confidence desc, id desc"

    partner_a_id = fields.Many2one("res.partner", required=True, ondelete="cascade", index=True)
    partner_b_id = fields.Many2one("res.partner", required=True, ondelete="cascade", index=True)
    partner_a_image = fields.Binary(related="partner_a_id.image_128", string="Photo A")
    partner_b_image = fields.Binary(related="partner_b_id.image_128", string="Photo B")
    partner_a_name = fields.Char(related="partner_a_id.name", string="Name A")
    partner_b_name = fields.Char(related="partner_b_id.name", string="Name B")
    partner_a_email = fields.Char(related="partner_a_id.email", string="Email A")
    partner_b_email = fields.Char(related="partner_b_id.email", string="Email B")
    partner_a_phone = fields.Char(related="partner_a_id.phone", string="Phone A")
    partner_b_phone = fields.Char(related="partner_b_id.phone", string="Phone B")
    partner_a_mobile = fields.Char(related="partner_a_id.mobile", string="Mobile A")
    partner_b_mobile = fields.Char(related="partner_b_id.mobile", string="Mobile B")
    partner_a_function = fields.Char(related="partner_a_id.function", string="Title A")
    partner_b_function = fields.Char(related="partner_b_id.function", string="Title B")
    partner_a_company = fields.Char(compute="_compute_compare_fields", string="Company A")
    partner_b_company = fields.Char(compute="_compute_compare_fields", string="Company B")
    partner_a_address = fields.Char(compute="_compute_compare_fields", string="Address A")
    partner_b_address = fields.Char(compute="_compute_compare_fields", string="Address B")
    partner_a_website = fields.Char(related="partner_a_id.website", string="Website A")
    partner_b_website = fields.Char(related="partner_b_id.website", string="Website B")
    partner_a_vat = fields.Char(related="partner_a_id.vat", string="Tax ID A")
    partner_b_vat = fields.Char(related="partner_b_id.vat", string="Tax ID B")

    confidence = fields.Float(string="Confidence %", digits=(5, 2), index=True)
    confidence_label = fields.Selection(
        [
            ("duplicate", "Duplicate"),
            ("possible", "Possible Duplicate"),
            ("low", "Low Match"),
        ],
        string="Label",
        index=True,
    )
    match_reasons = fields.Text(string="Match Reasons")
    match_reasons_html = fields.Html(
        string="Match Details",
        compute="_compute_compare_fields",
        sanitize=False,
    )
    confidence_gauge_html = fields.Html(
        string="Confidence Gauge",
        compute="_compute_compare_fields",
        sanitize=False,
    )
    review_position = fields.Char(
        string="Review Position",
        compute="_compute_review_position",
    )
    show_match_details = fields.Boolean(string="Show Match Details")

    state = fields.Selection(
        [
            ("open", "Open"),
            ("review", "Need Review"),
            ("merged", "Merged"),
            ("ignored", "Ignored"),
            ("not_duplicate", "Not Duplicate"),
        ],
        default="open",
        index=True,
    )
    detection_source = fields.Selection(
        [
            ("manual", "Manual Scan"),
            ("cron", "Scheduled"),
            ("import", "Import"),
            ("api", "API"),
        ],
        default="manual",
    )
    company_id = fields.Many2one(
        "res.company",
        compute="_compute_company_id",
        store=True,
    )

    @api.depends("partner_a_id", "partner_b_id")
    def _compute_company_id(self):
        for record in self:
            record.company_id = (
                record.partner_a_id.company_id
                or record.partner_b_id.company_id
                or self.env.company
            )

    @api.depends(
        "partner_a_id",
        "partner_b_id",
        "partner_a_id.parent_id",
        "partner_b_id.parent_id",
        "partner_a_id.commercial_company_name",
        "partner_b_id.commercial_company_name",
        "partner_a_id.street",
        "partner_b_id.street",
        "partner_a_id.city",
        "partner_b_id.city",
        "partner_a_id.zip",
        "partner_b_id.zip",
        "partner_a_id.country_id",
        "partner_b_id.country_id",
        "confidence",
        "confidence_label",
        "match_reasons",
    )
    def _compute_compare_fields(self):
        for record in self:
            a = record.partner_a_id
            b = record.partner_b_id
            record.partner_a_company = a.parent_id.name or a.commercial_company_name or ""
            record.partner_b_company = b.parent_id.name or b.commercial_company_name or ""
            record.partner_a_address = record._format_address(a)
            record.partner_b_address = record._format_address(b)
            record.confidence_gauge_html = record._build_confidence_gauge()
            record.match_reasons_html = record._build_match_reasons_html()

    @api.depends("state", "confidence")
    def _compute_review_position(self):
        active = self.search([("state", "in", ("open", "review"))], order="confidence desc, id desc")
        indexed = {rec.id: idx for idx, rec in enumerate(active, start=1)}
        total = len(active)
        for record in self:
            position = indexed.get(record.id)
            if position:
                record.review_position = "%s of %s" % (position, total)
            else:
                record.review_position = ""

    @staticmethod
    def _format_address(partner):
        if not partner:
            return ""
        parts = [
            partner.street or "",
            partner.street2 or "",
            partner.city or "",
            partner.zip or "",
            partner.state_id.name if partner.state_id else "",
            partner.country_id.name if partner.country_id else "",
        ]
        return ", ".join(part for part in parts if part)

    def _build_confidence_gauge(self):
        self.ensure_one()
        value = max(0.0, min(100.0, self.confidence or 0.0))
        label = dict(self._fields["confidence_label"].selection).get(
            self.confidence_label, "Match"
        )
        return (
            "<div class='o_sm_gauge'>"
            "<div class='o_sm_gauge_ring' style='--sm-conf:%(value)s;'>"
            "<div class='o_sm_gauge_inner'>"
            "<div class='o_sm_gauge_value'>%(value_int)s%%</div>"
            "<div class='o_sm_gauge_label'>%(label)s</div>"
            "</div></div></div>"
        ) % {
            "value": value,
            "value_int": int(round(value)),
            "label": label,
        }

    def _build_match_reasons_html(self):
        self.ensure_one()
        reasons = []
        for line in (self.match_reasons or "").splitlines():
            text = line.strip().lstrip("✓").strip()
            if text:
                reasons.append(text)
        if not reasons:
            reasons = ["No detailed match reasons"]
        items = "".join(
            "<li><i class='fa fa-check-circle'></i><span>%s</span></li>" % reason
            for reason in reasons
        )
        return "<ul class='o_sm_match_list'>%s</ul>" % items

    def action_open_merge_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Merge Contacts",
            "res_model": "duplicate.contact.merge.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_pair_id": self.id,
                "default_partner_a_id": self.partner_a_id.id,
                "default_partner_b_id": self.partner_b_id.id,
            },
        }

    def action_ignore(self):
        for record in self:
            low, high = sorted((record.partner_a_id.id, record.partner_b_id.id))
            existing = self.env["duplicate.contact.ignore"].sudo().search([
                ("partner_low_id", "=", low),
                ("partner_high_id", "=", high),
            ], limit=1)
            if not existing:
                self.env["duplicate.contact.ignore"].sudo().create({
                    "partner_low_id": low,
                    "partner_high_id": high,
                    "reason": "Ignored from duplicate review",
                })
            record.state = "ignored"
        return self.action_next_pair()

    def action_mark_not_duplicate(self):
        self.write({"state": "not_duplicate"})
        return self.action_next_pair()

    def action_toggle_match_details(self):
        self.ensure_one()
        self.show_match_details = not self.show_match_details
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_next_pair(self):
        self.ensure_one()
        domain = [
            ("state", "in", ("open", "review")),
            ("id", "!=", self.id),
        ]
        nxt = self.search(
            domain + [("confidence", "<", self.confidence)],
            order="confidence desc, id desc",
            limit=1,
        )
        if not nxt:
            nxt = self.search(domain, order="confidence desc, id desc", limit=1)
        if not nxt:
            return {
                "type": "ir.actions.act_window",
                "name": "Duplicate Pairs",
                "res_model": self._name,
                "view_mode": "list,form",
                "domain": [("state", "in", ("open", "review"))],
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": "Duplicate Review",
            "res_model": self._name,
            "res_id": nxt.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_partner_a(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "res_id": self.partner_a_id.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_open_partner_b(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "res_id": self.partner_b_id.id,
            "view_mode": "form",
            "target": "new",
        }

    @api.model
    def cron_detect_duplicates(self):
        from ..services.detection import DuplicateDetectionService
        return DuplicateDetectionService(self.env).run_scan(
            limit=int(
                self.env["ir.config_parameter"].sudo().get_param(
                    "sm_duplicate_contact.scan_limit", "2000"
                )
                or 2000
            ),
            source="cron",
        )
