# TODO

## Zabezpieczenie publicznych endpointów (strava.krasnal.cc)

Kontekst: appka wystawiona publicznie bez auth. Audyt wykazał, że odczyt dashboardu może
zostać publiczny świadomie, ale endpointy, które **zmieniają stan** albo **kosztują Strava API
quota**, muszą być zabeznieczone.

- [ ] Dodać shared-secret / basic auth (na poziomie Caddy) dla:
  - [ ] `POST /settings` — nadpisywanie Client ID/Secret, listy komponentów
  - [ ] `/oauth/authorize` i `/oauth/callback` — żeby nikt obcy nie mógł podmienić zapisanych tokenów Strava
  - [ ] `POST /api/sync` — trigger uderzający w Strava API zapisanymi tokenami
- [ ] Dodać rate limiting na `/api/sync` (np. min. interwał między wywołaniami, albo limit per IP)
- [ ] Dodać CSRF token na formularzu `/settings`
- [ ] (opcjonalnie) rozważyć, czy sam odczyt dashboardu ma zostać publiczny — dane osobowe
      (nazwa, aktywności, sprzęt, linki do strava.com/activities/<id>) są widoczne dla każdego
