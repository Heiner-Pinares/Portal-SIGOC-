from decimal import Decimal

from app.domain import ServiceRecord


class DemoPVUDBRepository:
    """Proveedor local explícito. Sus datos nunca se etiquetan como Oracle."""

    CAMPAIGNS = {
        "3504": (
            "CAMPAÑA DEMO HOGAR",
            [
                ("PL100", "Internet Fibra 400 Mbps", "1001", "Internet Fibra 400 Mbps", "70.00", "2 PLAY DIGITAL"),
                ("PL100", "Internet Fibra 400 Mbps", "1002", "Claro TV Superior Pro", "140.00", "2 PLAY DIGITAL"),
                ("PL200", "Internet Fibra 500 Mbps", "2001", "Internet 500 Mbps", "110.00", "1 PLAY DIGITAL"),
            ],
        ),
        "356": (
            "HFC EVENTOS ESPECIALES",
            [
                ("PL356", "Paquete HFC", "3561", "Claro TV Superior Pro", "140.00", "2 PLAY DIGITAL"),
                ("PL356", "Paquete HFC", "3562", "Internet 400 Mbps", "70.00", "2 PLAY DIGITAL"),
                ("PL500", "Internet 500", "3563", "Internet 500 Mbps", "110.00", "1 PLAY DIGITAL"),
            ],
        ),
    }

    def find_campaign(self, campaign_code):
        source = self.CAMPAIGNS.get(str(campaign_code))
        if not source:
            return []
        name, rows = source
        result = []
        for plan, plan_name, sncode, service_name, charge, solution in rows:
            gross = Decimal(charge)
            net = (gross / Decimal("1.18")).quantize(Decimal("0.01"))
            result.append(ServiceRecord(
                plan=plan, plan_name=plan_name, campaign=str(campaign_code), campaign_name=name,
                solution=solution, tmcode="T-DEMO", spcode="SP-DEMO", sncode=sncode,
                service=sncode, service_name=service_name, charge_without_tax=net,
                charge_with_tax=gross, service_type="SERVICIO DEMO",
                key=f"{plan}-{campaign_code}-{sncode}",
            ))
        return result

