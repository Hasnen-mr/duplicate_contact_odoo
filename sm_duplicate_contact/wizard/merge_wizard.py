# -*- coding: utf-8 -*-
from odoo import api, fields, models


class DuplicateContactMergeWizard(models.TransientModel):
    _name = "duplicate.contact.merge.wizard"
    _description = "Merge Duplicate Contacts"

    pair_id = fields.Many2one("duplicate.contact.pair")
    partner_a_id = fields.Many2one("res.partner", required=True, string="Contact A")
    partner_b_id = fields.Many2one("res.partner", required=True, string="Contact B")
    step = fields.Selection(
        [
            ("select", "Select Data"),
            ("review", "Review"),
            ("confirm", "Confirm"),
        ],
        default="select",
        required=True,
    )
    survivor_id = fields.Selection(
        [("a", "Contact A"), ("b", "Contact B")],
        default="a",
        required=True,
        string="Keep as master",
    )
    merge_note = fields.Text(string="Add a note (optional)")
    combine_notes = fields.Boolean(string="Combine notes", default=True)

    name_choice = fields.Selection([("a", "Use A"), ("b", "Use B")], default="a")
    email_choice = fields.Selection([("a", "Use A"), ("b", "Use B")], default="a")
    phone_choice = fields.Selection([("a", "Use A"), ("b", "Use B")], default="a")
    mobile_choice = fields.Selection([("a", "Use A"), ("b", "Use B")], default="a")
    street_choice = fields.Selection([("a", "Use A"), ("b", "Use B")], default="a")
    website_choice = fields.Selection([("a", "Use A"), ("b", "Use B")], default="a")
    vat_choice = fields.Selection([("a", "Use A"), ("b", "Use B")], default="a")
    function_choice = fields.Selection([("a", "Use A"), ("b", "Use B")], default="a", string="Title")
    company_choice = fields.Selection([("a", "Use A"), ("b", "Use B")], default="a", string="Company")

    preview_name_a = fields.Char(compute="_compute_preview")
    preview_name_b = fields.Char(compute="_compute_preview")
    preview_phone_a = fields.Char(compute="_compute_preview")
    preview_phone_b = fields.Char(compute="_compute_preview")
    preview_mobile_a = fields.Char(compute="_compute_preview")
    preview_mobile_b = fields.Char(compute="_compute_preview")
    preview_email_a = fields.Char(compute="_compute_preview")
    preview_email_b = fields.Char(compute="_compute_preview")
    preview_street_a = fields.Char(compute="_compute_preview")
    preview_street_b = fields.Char(compute="_compute_preview")
    preview_website_a = fields.Char(compute="_compute_preview")
    preview_website_b = fields.Char(compute="_compute_preview")
    preview_vat_a = fields.Char(compute="_compute_preview")
    preview_vat_b = fields.Char(compute="_compute_preview")
    preview_function_a = fields.Char(compute="_compute_preview")
    preview_function_b = fields.Char(compute="_compute_preview")
    preview_company_a = fields.Char(compute="_compute_preview")
    preview_company_b = fields.Char(compute="_compute_preview")

    recommend_name = fields.Selection([("a", "A"), ("b", "B")], compute="_compute_preview")
    recommend_email = fields.Selection([("a", "A"), ("b", "B")], compute="_compute_preview")
    recommend_phone = fields.Selection([("a", "A"), ("b", "B")], compute="_compute_preview")
    recommend_mobile = fields.Selection([("a", "A"), ("b", "B")], compute="_compute_preview")
    recommend_street = fields.Selection([("a", "A"), ("b", "B")], compute="_compute_preview")
    recommend_website = fields.Selection([("a", "A"), ("b", "B")], compute="_compute_preview")
    recommend_vat = fields.Selection([("a", "A"), ("b", "B")], compute="_compute_preview")
    recommend_function = fields.Selection([("a", "A"), ("b", "B")], compute="_compute_preview")
    recommend_company = fields.Selection([("a", "A"), ("b", "B")], compute="_compute_preview")

    summary_html = fields.Html(compute="_compute_summary_html", sanitize=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        partner_a = self.env["res.partner"].browse(res.get("partner_a_id"))
        partner_b = self.env["res.partner"].browse(res.get("partner_b_id"))
        if partner_a and partner_b:
            defaults = self._recommended_choices(partner_a, partner_b)
            for key, value in defaults.items():
                res.setdefault(key, value)
            res.setdefault("survivor_id", defaults.get("name_choice", "a"))
        return res

    @staticmethod
    def _pick_richer(value_a, value_b):
        a = (value_a or "").strip()
        b = (value_b or "").strip()
        if a and not b:
            return "a"
        if b and not a:
            return "b"
        if len(b) > len(a):
            return "b"
        return "a"

    @classmethod
    def _recommended_choices(cls, partner_a, partner_b):
        return {
            "name_choice": cls._pick_richer(partner_a.name, partner_b.name),
            "email_choice": cls._pick_richer(partner_a.email, partner_b.email),
            "phone_choice": cls._pick_richer(partner_a.phone, partner_b.phone),
            "mobile_choice": cls._pick_richer(partner_a.mobile, partner_b.mobile),
            "street_choice": cls._pick_richer(partner_a.street, partner_b.street),
            "website_choice": cls._pick_richer(partner_a.website, partner_b.website),
            "vat_choice": cls._pick_richer(partner_a.vat, partner_b.vat),
            "function_choice": cls._pick_richer(partner_a.function, partner_b.function),
            "company_choice": cls._pick_richer(
                partner_a.parent_id.name or partner_a.commercial_company_name,
                partner_b.parent_id.name or partner_b.commercial_company_name,
            ),
        }

    @api.depends(
        "partner_a_id",
        "partner_b_id",
        "partner_a_id.name",
        "partner_b_id.name",
        "partner_a_id.phone",
        "partner_b_id.phone",
        "partner_a_id.mobile",
        "partner_b_id.mobile",
        "partner_a_id.email",
        "partner_b_id.email",
        "partner_a_id.street",
        "partner_b_id.street",
        "partner_a_id.website",
        "partner_b_id.website",
        "partner_a_id.vat",
        "partner_b_id.vat",
        "partner_a_id.function",
        "partner_b_id.function",
        "partner_a_id.parent_id",
        "partner_b_id.parent_id",
        "partner_a_id.commercial_company_name",
        "partner_b_id.commercial_company_name",
    )
    def _compute_preview(self):
        for wiz in self:
            a, b = wiz.partner_a_id, wiz.partner_b_id
            wiz.preview_name_a = a.name or ""
            wiz.preview_name_b = b.name or ""
            wiz.preview_phone_a = a.phone or ""
            wiz.preview_phone_b = b.phone or ""
            wiz.preview_mobile_a = a.mobile or ""
            wiz.preview_mobile_b = b.mobile or ""
            wiz.preview_email_a = a.email or ""
            wiz.preview_email_b = b.email or ""
            wiz.preview_street_a = a.street or ""
            wiz.preview_street_b = b.street or ""
            wiz.preview_website_a = a.website or ""
            wiz.preview_website_b = b.website or ""
            wiz.preview_vat_a = a.vat or ""
            wiz.preview_vat_b = b.vat or ""
            wiz.preview_function_a = a.function or ""
            wiz.preview_function_b = b.function or ""
            wiz.preview_company_a = a.parent_id.name or a.commercial_company_name or ""
            wiz.preview_company_b = b.parent_id.name or b.commercial_company_name or ""
            recommended = self._recommended_choices(a, b) if a and b else {}
            wiz.recommend_name = recommended.get("name_choice")
            wiz.recommend_email = recommended.get("email_choice")
            wiz.recommend_phone = recommended.get("phone_choice")
            wiz.recommend_mobile = recommended.get("mobile_choice")
            wiz.recommend_street = recommended.get("street_choice")
            wiz.recommend_website = recommended.get("website_choice")
            wiz.recommend_vat = recommended.get("vat_choice")
            wiz.recommend_function = recommended.get("function_choice")
            wiz.recommend_company = recommended.get("company_choice")

    @api.depends(
        "survivor_id",
        "name_choice",
        "email_choice",
        "phone_choice",
        "mobile_choice",
        "street_choice",
        "website_choice",
        "vat_choice",
        "function_choice",
        "company_choice",
        "partner_a_id",
        "partner_b_id",
    )
    def _compute_summary_html(self):
        for wiz in self:
            survivor, duplicate = wiz._partners()
            rows = []
            for label, field in (
                ("Name", "name"),
                ("Email", "email"),
                ("Phone", "phone"),
                ("Mobile", "mobile"),
                ("Title", "function"),
                ("Company", "company"),
                ("Street", "street"),
                ("Website", "website"),
                ("Tax ID", "vat"),
            ):
                value = wiz._selected_value(field)
                rows.append(
                    "<tr><td><strong>%s</strong></td><td>%s</td></tr>"
                    % (label, value or "<em class='text-muted'>—</em>")
                )
            wiz.summary_html = (
                "<div class='o_sm_merge_summary'>"
                "<p>Master contact: <strong>%s</strong></p>"
                "<p>Merged into master: <strong>%s</strong></p>"
                "<table class='table table-sm table-borderless mb-0'>%s</table>"
                "</div>"
            ) % (survivor.display_name, duplicate.display_name, "".join(rows))

    def _selected_value(self, field):
        self.ensure_one()
        choice_map = {
            "name": self.name_choice,
            "email": self.email_choice,
            "phone": self.phone_choice,
            "mobile": self.mobile_choice,
            "street": self.street_choice,
            "website": self.website_choice,
            "vat": self.vat_choice,
            "function": self.function_choice,
            "company": self.company_choice,
        }
        choice = choice_map.get(field, "a")
        source = self.partner_a_id if choice == "a" else self.partner_b_id
        if field == "company":
            return source.parent_id.name or source.commercial_company_name or ""
        return getattr(source, field) or ""

    def _partners(self):
        self.ensure_one()
        if self.survivor_id == "a":
            return self.partner_a_id, self.partner_b_id
        return self.partner_b_id, self.partner_a_id

    def _field_choices(self):
        self.ensure_one()
        return {
            "name": self.name_choice,
            "email": self.email_choice,
            "phone": self.phone_choice,
            "mobile": self.mobile_choice,
            "street": self.street_choice,
            "website": self.website_choice,
            "vat": self.vat_choice,
            "function": self.function_choice,
            "company": self.company_choice,
        }

    def action_next_step(self):
        self.ensure_one()
        if self.step == "select":
            self.step = "review"
        elif self.step == "review":
            self.step = "confirm"
        return self._reopen()

    def action_previous_step(self):
        self.ensure_one()
        if self.step == "confirm":
            self.step = "review"
        elif self.step == "review":
            self.step = "select"
        return self._reopen()

    def _reopen(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_merge(self):
        self.ensure_one()
        from ..services.merge import DuplicateMergeService

        survivor, duplicate = self._partners()
        DuplicateMergeService(self.env).merge_partners(
            survivor,
            duplicate,
            field_choices=self._field_choices(),
            combine_notes=self.combine_notes,
            partner_a=self.partner_a_id,
            partner_b=self.partner_b_id,
            merge_note=self.merge_note,
        )
        if self.pair_id:
            self.pair_id.state = "merged"
        return {
            "type": "ir.actions.act_window",
            "name": survivor.name,
            "res_model": "res.partner",
            "res_id": survivor.id,
            "view_mode": "form",
            "target": "current",
        }
