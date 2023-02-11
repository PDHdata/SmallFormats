from django.db import models


class PartnerType(models.IntegerChoices):
    NONE = 0
    PARTNER = 1, "keyword Partner"
    CHOOSE_A_BACKGROUND = 10, "choose a Background"
    BACKGROUND = 11
    # the BBD partner-with pairs
    PARTNER_WITH_BLARING = 100, "Blaring Captain/Recruiter"
    PARTNER_WITH_CHAKRAM = 101, "Chakram Retriever/Slinger"
    PARTNER_WITH_PROTEGE = 102, "Impetuous Protege/Proud Mentor"
    PARTNER_WITH_SOULBLADE = 103, "Soulblade Corrupter/Renewer"
    PARTNER_WITH_WEAVER = 104, "Ley/Lore Weaver"
