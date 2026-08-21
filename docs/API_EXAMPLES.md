# Exemples de requêtes API INJS-LMD

Base URL: `http://localhost:8001/api/v1`

## Authentification

```bash
# Login
curl -X POST http://localhost:8001/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "etudiant1@demo.injs.ci", "password": "Demo@INJS2026!"}'

# Réponse
# {"access": "...", "refresh": "...", "user": {...}, "permissions": [...]}

# Refresh token
curl -X POST http://localhost:8001/api/v1/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "YOUR_REFRESH_TOKEN"}'

# Profil
curl http://localhost:8001/api/v1/auth/me/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Étudiants

```bash
# Liste étudiants
curl "http://localhost:8001/api/v1/students/?program=<uuid>" \
  -H "Authorization: Bearer TOKEN"

# Carte étudiant digitale
curl http://localhost:8001/api/v1/students/<uuid>/card/ \
  -H "Authorization: Bearer TOKEN"

# Export Excel
curl http://localhost:8001/api/v1/students/export/excel/ \
  -H "Authorization: Bearer TOKEN" -o etudiants.xlsx
```

## Notes & Délibérations

```bash
# Saisir une note
curl -X POST http://localhost:8001/api/v1/exams/grades/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"student": "UUID", "evaluation": "UUID", "score": "14.50"}'

# Lancer délibération
curl -X POST http://localhost:8001/api/v1/exams/deliberations/<uuid>/run/ \
  -H "Authorization: Bearer TOKEN"
```

## Paiements

```bash
# Providers disponibles
curl http://localhost:8001/api/v1/finance/providers/ \
  -H "Authorization: Bearer TOKEN"

# Initier paiement Orange Money
curl -X POST http://localhost:8001/api/v1/finance/payments/initiate/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "student_fee_id": "UUID",
    "provider": "orange_money",
    "phone": "+2250700000000"
  }'

# Wave / MTN / Moov / Visa
# provider: "wave" | "mtn_momo" | "moov_money" | "visa_card"
```

## Rapports

```bash
# Dashboard analytics
curl http://localhost:8001/api/v1/reports/analytics/ \
  -H "Authorization: Bearer TOKEN"

# Relevé de notes PDF (semestre 1, année 2025-2026)
curl "http://localhost:8001/api/v1/reports/transcript/<student_uuid>/pdf/?semester=1&academic_year=2025-2026" \
  -H "Authorization: Bearer TOKEN" -o releve.pdf

# Données JSON du relevé (sans PDF)
curl "http://localhost:8001/api/v1/reports/transcript/<student_uuid>/pdf/?semester=1&academic_year=2025-2026&format=json" \
  -H "Authorization: Bearer TOKEN"

# Historique académique
curl http://localhost:8001/api/v1/reports/transcript/<student_uuid>/summary/ \
  -H "Authorization: Bearer TOKEN"
```

## Académique STAPS

```bash
# Spécialités (TC, EM, ES, MS, APA)
curl http://localhost:8001/api/v1/academics/specializations/ \
  -H "Authorization: Bearer TOKEN"

# Nomenclature emplois (grades A3/A4, CAPS/CAPEPS)
curl "http://localhost:8001/api/v1/academics/job-nomenclatures/?degree_type=L" \
  -H "Authorization: Bearer TOKEN"

# Parcours emploi d'un étudiant (selon filière + spécialité)
curl http://localhost:8001/api/v1/students/<uuid>/career_path/ \
  -H "Authorization: Bearer TOKEN"
```

## Emplois du temps (EDT)

```bash
# Périodes de formation
curl http://localhost:8002/api/v1/academics/formation-periods/ \
  -H "Authorization: Bearer TOKEN"

# Générer les séances d'une période × promotion
curl -X POST http://localhost:8002/api/v1/faculty/seances/generate/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"period": "UUID", "promotion": "UUID"}'

# Publier
curl -X POST http://localhost:8002/api/v1/faculty/seances/publish/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"period": "UUID", "promotion": "UUID"}'

# Calendrier (étudiants : séances publiées de leur promotion)
curl "http://localhost:8002/api/v1/faculty/seances/?visible=true" \
  -H "Authorization: Bearer TOKEN"

# QR d’une séance publiée
curl http://localhost:8002/api/v1/faculty/seances/UUID/qr/ \
  -H "Authorization: Bearer TOKEN"

# Journal de badgeage
curl http://localhost:8002/api/v1/faculty/badge-events/ \
  -H "Authorization: Bearer TOKEN"
```

Guide complet : [EDT.md](EDT.md).
