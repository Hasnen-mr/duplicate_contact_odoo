# -*- coding: utf-8 -*-
from odoo import api, fields, models, release
from odoo.tools.misc import format_datetime

DASHBOARD_PAIR_LIMIT = 20
LAST_SCAN_PARAM = "sm_duplicate_contact.last_scan_at"


class DuplicateContactDashboard(models.TransientModel):
    _name = "duplicate.contact.dashboard"
    _description = "Duplicate Contact Dashboard"

    total_contacts = fields.Integer(readonly=True)
    duplicates_found = fields.Integer(readonly=True)
    need_review = fields.Integer(readonly=True)
    merged_count = fields.Integer(readonly=True)
    ignored_count = fields.Integer(readonly=True)
    pair_ids = fields.Many2many(
        "duplicate.contact.pair",
        string="Duplicate Pairs",
        readonly=True,
    )
    pair_page = fields.Integer(default=1, string="Page")
    pair_page_count = fields.Integer(readonly=True, string="Pages")
    pair_page_info = fields.Char(compute="_compute_pair_page_info", string="Page Info")
    has_pairs = fields.Boolean(readonly=True)
    last_scan_display = fields.Char(readonly=True, string="Last Scan")
    next_scan_display = fields.Char(readonly=True, string="Next Auto Scan")
    auto_scan_enabled = fields.Boolean(readonly=True)

    @api.depends("pair_page", "pair_page_count", "duplicates_found")
    def _compute_pair_page_info(self):
        for record in self:
            total = record.duplicates_found or 0
            page = max(1, record.pair_page or 1)
            pages = max(1, record.pair_page_count or 1)
            start = ((page - 1) * DASHBOARD_PAIR_LIMIT) + 1 if total else 0
            end = min(page * DASHBOARD_PAIR_LIMIT, total)
            record.pair_page_info = "Showing %s–%s of %s  ·  Page %s / %s" % (
                start, end, total, page, pages,
            )

    @api.model
    def _active_pair_domain(self):
        return [("state", "in", ("open", "review"))]

    @api.model
    def _format_local_dt(self, dt_value):
        if not dt_value:
            return "Never"
        if isinstance(dt_value, str):
            dt_value = fields.Datetime.to_datetime(dt_value)
        # format_datetime applies the user's timezone automatically
        return format_datetime(self.env, dt_value, dt_format="MMM d, yyyy hh:mm a")

    @api.model
    def _scan_schedule_info(self):
        icp = self.env["ir.config_parameter"].sudo()
        last_raw = icp.get_param(LAST_SCAN_PARAM)
        last_display = self._format_local_dt(last_raw) if last_raw else "Never"

        cron = self.env.ref(
            "sm_duplicate_contact.ir_cron_duplicate_contact_scan",
            raise_if_not_found=False,
        )
        auto_enabled = bool(cron and cron.active)
        if cron and cron.active and cron.nextcall:
            next_display = self._format_local_dt(cron.nextcall)
        elif cron and not cron.active:
            next_display = "Auto scan is off"
            auto_enabled = False
        else:
            next_display = "Not scheduled"

        return {
            "last_scan_display": last_display,
            "next_scan_display": next_display,
            "auto_scan_enabled": auto_enabled,
        }

    @api.model
    def mark_scan_completed(self):
        self.env["ir.config_parameter"].sudo().set_param(
            LAST_SCAN_PARAM,
            fields.Datetime.to_string(fields.Datetime.now()),
        )

    @api.model
    def _dashboard_values(self, page=1):
        Partner = self.env["res.partner"].sudo()
        Pair = self.env["duplicate.contact.pair"].sudo()
        History = self.env["duplicate.contact.merge.history"].sudo()
        domain = self._active_pair_domain()
        total_pairs = Pair.search_count(domain)
        page = max(1, int(page or 1))
        page_count = max(1, (total_pairs + DASHBOARD_PAIR_LIMIT - 1) // DASHBOARD_PAIR_LIMIT) if total_pairs else 1
        if page > page_count:
            page = page_count
        offset = (page - 1) * DASHBOARD_PAIR_LIMIT
        pairs = Pair.search(
            domain,
            order="confidence desc, id desc",
            limit=DASHBOARD_PAIR_LIMIT,
            offset=offset,
        )
        values = {
            "total_contacts": Partner.search_count([("active", "=", True)]),
            "duplicates_found": total_pairs,
            "need_review": Pair.search_count([("state", "=", "review")]),
            "merged_count": History.search_count([]),
            "ignored_count": Pair.search_count([("state", "=", "ignored")]),
            "pair_ids": [(6, 0, pairs.ids)],
            "pair_page": page,
            "pair_page_count": page_count,
            "has_pairs": bool(total_pairs),
        }
        values.update(self._scan_schedule_info())
        return values

    @api.model
    def action_open_dashboard(self):
        dashboard = self.create(self._dashboard_values(page=1))
        return {
            "type": "ir.actions.act_window",
            "name": "Duplicate Contact Manager",
            "res_model": self._name,
            "res_id": dashboard.id,
            "view_mode": "form",
            "target": "current",
        }

    def _reopen(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Duplicate Contact Manager",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_run_scan(self):
        from ..services.detection import DuplicateDetectionService
        Pair = self.env["duplicate.contact.pair"].sudo()
        Pair.cleanup_stale_matches()
        DuplicateDetectionService(self.env).run_scan(source="manual")
        self.mark_scan_completed()
        self.write(self._dashboard_values(page=1))
        return self._reopen()

    def action_refresh_pairs(self):
        self.ensure_one()
        self.env["duplicate.contact.pair"].sudo().cleanup_stale_matches()
        self.write(self._dashboard_values(page=self.pair_page or 1))
        return self._reopen()

    def action_pair_page_prev(self):
        self.ensure_one()
        page = max(1, (self.pair_page or 1) - 1)
        self.write(self._dashboard_values(page=page))
        return self._reopen()

    def action_pair_page_next(self):
        self.ensure_one()
        page = min(self.pair_page_count or 1, (self.pair_page or 1) + 1)
        self.write(self._dashboard_values(page=page))
        return self._reopen()

    def action_open_duplicates(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Duplicate Review",
            "res_model": "duplicate.contact.pair",
            "view_mode": "list,form",
            "domain": self._active_pair_domain(),
            "limit": DASHBOARD_PAIR_LIMIT,
        }

    def action_open_review(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Need Review",
            "res_model": "duplicate.contact.pair",
            "view_mode": "list,form",
            "domain": [("state", "=", "review")],
            "limit": DASHBOARD_PAIR_LIMIT,
        }

    def action_open_merged(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Merge History",
            "res_model": "duplicate.contact.merge.history",
            "view_mode": "list",
            "limit": DASHBOARD_PAIR_LIMIT,
        }

    def action_open_auto_scan_settings(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Duplicate Contact Settings",
            "res_model": "res.config.settings",
            "view_mode": "form",
            "target": "current",
            "context": {"module": "sm_duplicate_contact"},
        }

    def action_open_twilio_apps(self):
        """Open Twilio Dialer on the Odoo Apps Store for this Odoo series."""
        series = release.major_version  # e.g. "18.0"
        return {
            "type": "ir.actions.act_url",
            "url": "https://apps.odoo.com/apps/modules/%s/twilio_dialer" % series,
            "target": "new",
        }
