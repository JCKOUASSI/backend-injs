"""
Catalogue des espaces pédagogiques INJS (cartographie campus LMD).
Chaque entrée : (code, name, capacity, building, room_type, floor, equipment, lat, lng, notes)
"""

# Helpers pour générer des séries numérotées
def _series(prefix, start, count, name_fn, capacity, building, room_type, floor='', equipment=None, lat=None, lng=None):
    rows = []
    for i in range(count):
        n = start + i
        code = f'{prefix}-{n:03d}'
        rows.append((
            code,
            name_fn(n),
            capacity,
            building,
            room_type,
            floor,
            equipment or [],
            lat,
            lng,
            '',
        ))
    return rows


CAMPUS_ROOMS = [
    # ── 1.A Bloc ENSEPS ──────────────────────────────────────────────
    ('AMP-001', 'Amphithéâtre ENSEPS A', 300, 'ENSEPS', 'amphitheater', 'RDC', ['sono', 'projecteur', 'climatisation'], 5.3478, -3.9865, ''),
    ('AMP-002', 'Amphithéâtre ENSEPS B', 250, 'ENSEPS', 'amphitheater', 'RDC', ['sono', 'projecteur', 'climatisation'], 5.3479, -3.9864, ''),
    ('SC-101', 'Salle de cours magistraux ENSEPS 1', 60, 'ENSEPS', 'classroom', '1', ['tableau', 'projecteur'], 5.3480, -3.9866, ''),
    ('SC-102', 'Salle de cours magistraux ENSEPS 2', 60, 'ENSEPS', 'classroom', '1', ['tableau', 'projecteur'], None, None, ''),
    ('SC-103', 'Salle de cours magistraux ENSEPS 3', 50, 'ENSEPS', 'classroom', '1', ['tableau'], None, None, ''),
    ('TD-001', 'Salle de TD ENSEPS 1', 30, 'ENSEPS', 'td', '1', ['tableau'], None, None, ''),
    ('TD-002', 'Salle de TD ENSEPS 2', 30, 'ENSEPS', 'td', '1', ['tableau'], None, None, ''),
    ('TD-003', 'Salle de TD ENSEPS 3', 25, 'ENSEPS', 'td', '2', ['tableau'], None, None, ''),
    ('TP-001', 'Salle de TP ENSEPS 1', 24, 'ENSEPS', 'tp', '2', ['matériel_sportif'], None, None, ''),
    ('TP-002', 'Salle de TP ENSEPS 2', 24, 'ENSEPS', 'tp', '2', ['matériel_sportif'], None, None, ''),
    ('SPEC-001', 'Salle de pédagogie sportive', 35, 'ENSEPS', 'specialized', '2', ['matériel_pédagogique'], None, None, ''),
    ('LAB-001', 'Salle de biomécanique ENSEPS', 20, 'ENSEPS', 'lab', '3', ['capteurs', 'plateforme_force'], None, None, ''),
    ('LAB-002', 'Salle de physiologie ENSEPS', 20, 'ENSEPS', 'lab', '3', ['ergomètre', 'spiromètre'], None, None, ''),
    ('SPEC-002', 'Salle de psychologie du sport', 25, 'ENSEPS', 'specialized', '3', ['vidéoprojecteur'], None, None, ''),
    ('LAB-003', 'Salle d\'analyse vidéo ENSEPS', 18, 'ENSEPS', 'lab', '3', ['stations_video', 'logiciel_analyse'], None, None, ''),
    ('INF-001', 'Salle informatique STAPS', 40, 'ENSEPS', 'computer', '2', ['pc', 'wifi', 'projecteur'], None, None, ''),
    ('INF-002', 'Salle multimédia ENSEPS', 30, 'ENSEPS', 'computer', '2', ['pc', 'écran_tactile'], None, None, ''),

    # ── 1.B Bloc ENSEP ───────────────────────────────────────────────
    ('AMP-003', 'Amphithéâtre ENSEP', 200, 'ENSEP', 'amphitheater', 'RDC', ['sono', 'projecteur'], 5.3482, -3.9870, ''),
    ('SC-111', 'Salle de cours STASE 1', 45, 'ENSEP', 'classroom', '1', ['tableau', 'projecteur'], None, None, ''),
    ('SC-112', 'Salle de cours STASE 2', 45, 'ENSEP', 'classroom', '1', ['tableau', 'projecteur'], None, None, ''),
    ('SC-113', 'Salle de cours STASE 3', 40, 'ENSEP', 'classroom', '1', ['tableau'], None, None, ''),
    ('SPEC-003', 'Salle de sociologie', 30, 'ENSEP', 'specialized', '1', ['tableau'], None, None, ''),
    ('SPEC-004', 'Salle de psychologie ENSEP', 30, 'ENSEP', 'specialized', '1', ['tableau'], None, None, ''),
    ('SPEC-005', 'Salle de communication ENSEP', 35, 'ENSEP', 'specialized', '2', ['sono', 'projecteur'], None, None, ''),
    ('SPEC-006', 'Salle d\'animation socioculturelle', 40, 'ENSEP', 'specialized', '2', ['matériel_animation'], None, None, ''),
    ('SPEC-007', 'Salle entrepreneuriat', 30, 'ENSEP', 'specialized', '2', ['projecteur', 'wifi'], None, None, ''),
    ('SPEC-008', 'Salle économie sociale', 30, 'ENSEP', 'specialized', '2', ['tableau'], None, None, ''),
    ('INF-003', 'Salle informatique ENSEP', 35, 'ENSEP', 'computer', '1', ['pc', 'wifi'], None, None, ''),
    ('INF-004', 'Salle multimédia ENSEP', 28, 'ENSEP', 'computer', '1', ['pc', 'écran'], None, None, ''),

    # ── 1.C Bâtiment LMD ─────────────────────────────────────────────
    ('AMP-004', 'Amphi 500 places LMD', 500, 'LMD', 'amphitheater', 'RDC', ['sono', 'visioconférence', 'climatisation'], 5.3485, -3.9858, ''),
    ('AMP-005', 'Amphi 300 places LMD', 300, 'LMD', 'amphitheater', 'RDC', ['sono', 'projecteur', 'climatisation'], 5.3486, -3.9857, ''),
    *_series('SC', 121, 20, lambda n: f'Salle de cours LMD {n - 120}', 40, 'LMD', 'classroom', '1-2', ['tableau', 'projecteur']),
    *_series('TD', 11, 10, lambda n: f'Salle de TD LMD {n - 10}', 30, 'LMD', 'td', '2', ['tableau']),
    *_series('TP', 11, 8, lambda n: f'Salle de TP LMD {n - 10}', 24, 'LMD', 'tp', '3', ['matériel_tp']),
    ('CONF-001', 'Centre de visioconférence LMD', 40, 'LMD', 'conference', '1', ['visioconférence', 'sono', 'écrans'], None, None, ''),
    ('INF-005', 'Centre e-learning LMD', 50, 'LMD', 'computer', '1', ['pc', 'casques', 'moodle'], None, None, ''),
    ('INF-006', 'Salle Moodle', 40, 'LMD', 'computer', '1', ['pc', 'moodle'], None, None, ''),
    ('SPEC-009', 'Studio audiovisuel LMD', 15, 'LMD', 'specialized', 'RDC', ['cameras', 'fond_vert', 'mixage'], None, None, ''),

    # ── 2. CNMS ──────────────────────────────────────────────────────
    ('MED-001', 'Salle Anatomie CNMS', 25, 'CNMS', 'medical', '1', ['mannequins', 'modèles_anatomiques'], 5.3490, -3.9860, ''),
    ('MED-002', 'Salle Physiologie CNMS', 20, 'CNMS', 'medical', '1', ['ergomètre', 'spiromètre'], None, None, ''),
    ('MED-003', 'Salle Biomécanique CNMS', 18, 'CNMS', 'medical', '1', ['capteurs', 'caméras'], None, None, ''),
    ('MED-004', 'Salle Nutrition', 20, 'CNMS', 'medical', '2', ['balances', 'logiciel_nutrition'], None, None, ''),
    ('MED-005', 'Salle Kinésithérapie', 15, 'CNMS', 'medical', '2', ['tables_kine', 'électrothérapie'], None, None, ''),
    ('MED-006', 'Salle Massage sportif', 12, 'CNMS', 'medical', '2', ['tables_massage'], None, None, ''),
    ('MED-007', 'Salle Rééducation', 15, 'CNMS', 'medical', '2', ['matériel_reeducation'], None, None, ''),
    ('MED-008', 'Salle Urgence sportive', 10, 'CNMS', 'medical', 'RDC', ['defibrillateur', 'trousse_urgence'], None, None, ''),
    ('MED-009', 'Laboratoire biomédical', 12, 'CNMS', 'lab', '3', ['analyseurs', 'centrifugeuse'], None, None, ''),
    ('MED-010', 'Salle ECG', 8, 'CNMS', 'medical', '3', ['ecg'], None, None, ''),
    ('MED-011', 'Salle Ergométrie', 10, 'CNMS', 'medical', '3', ['tapis', 'velo_ergo'], None, None, ''),

    # ── 3. CNSHN ─────────────────────────────────────────────────────
    ('SPORT-001', 'Salle préparation physique CNSHN', 40, 'CNSHN', 'sport', 'RDC', ['matériel_pp'], 5.3492, -3.9855, ''),
    ('SPORT-002', 'Salle musculation CNSHN', 30, 'CNSHN', 'sport', 'RDC', ['machines', 'haltères'], None, None, ''),
    ('SPORT-003', 'Salle récupération', 20, 'CNSHN', 'sport', '1', ['rouleaux', 'étirements'], None, None, ''),
    ('SPORT-004', 'Salle cryothérapie', 8, 'CNSHN', 'sport', '1', ['cabine_cryo'], None, None, ''),
    ('SPORT-005', 'Salle vidéo CNSHN', 25, 'CNSHN', 'specialized', '1', ['écrans', 'analyse_video'], None, None, ''),
    ('SPORT-006', 'Salle analyse tactique', 30, 'CNSHN', 'specialized', '1', ['tableau_tactique', 'projecteur'], None, None, ''),
    ('SPORT-007', 'Salle préparation mentale', 20, 'CNSHN', 'specialized', '2', ['relaxation'], None, None, ''),

    # ── 4. Gymnases ──────────────────────────────────────────────────
    ('GYM-001', 'Gymnase 1 — Sports collectifs', 200, 'GYM', 'gym', 'RDC', ['basketball', 'volleyball', 'handball', 'badminton'], 5.3475, -3.9875, ''),
    ('GYM-002', 'Gymnase 2 — Gymnastique & combats', 150, 'GYM', 'gym', 'RDC', ['gymnastique', 'arts_martiaux', 'escrime', 'lutte'], 5.3474, -3.9876, ''),

    # ── 5. Installations sportives extérieures ───────────────────────
    ('SPORT-010', 'Piste d\'athlétisme 400 m', 500, 'EXT', 'sport', '', ['piste_400', 'chronométrage'], 5.3468, -3.9880, ''),
    ('SPORT-011', 'Aires de saut', 80, 'EXT', 'sport', '', ['fosse_sable', 'piste_élan'], None, None, ''),
    ('SPORT-012', 'Aires de lancers', 60, 'EXT', 'sport', '', ['cage_lancer'], None, None, ''),
    ('SPORT-013', 'Salle chronométrage athlétisme', 10, 'EXT', 'specialized', '', ['chronométrage_electronique'], None, None, ''),
    ('SPORT-014', 'Terrain de football principal', 500, 'EXT', 'sport', '', ['pelouse', 'tribunes'], 5.3465, -3.9885, ''),
    ('SPORT-015', 'Terrain synthétique', 300, 'EXT', 'sport', '', ['synthétique', 'éclairage'], None, None, ''),
    ('SPORT-016', 'Terrain d\'entraînement football', 200, 'EXT', 'sport', '', ['pelouse'], None, None, ''),
    ('SPORT-017', 'Basketball extérieur', 100, 'EXT', 'sport', '', ['paniers'], None, None, ''),
    ('SPORT-018', 'Handball extérieur', 100, 'EXT', 'sport', '', ['buts'], None, None, ''),
    ('SPORT-019', 'Volleyball extérieur', 80, 'EXT', 'sport', '', ['filets'], None, None, ''),
    ('SPORT-020', 'Courts de tennis', 60, 'EXT', 'sport', '', ['filets', 'revêtement'], None, None, ''),
    ('SPORT-021', 'Piscine olympique', 400, 'EXT', 'sport', '', ['bassins_50m', 'vestiaires'], 5.3460, -3.9890, ''),
    ('SPORT-022', 'Bassin d\'apprentissage', 80, 'EXT', 'sport', '', ['bassin_25m'], None, None, ''),
    ('SPORT-023', 'Dojo', 50, 'EXT', 'sport', 'RDC', ['tatamis'], None, None, ''),
    ('SPORT-024', 'Salle de boxe', 40, 'EXT', 'sport', 'RDC', ['ring', 'sacs'], None, None, ''),
    ('SPORT-025', 'Salle de karaté', 40, 'EXT', 'sport', 'RDC', ['tatamis'], None, None, ''),
    ('SPORT-026', 'Salle de taekwondo', 40, 'EXT', 'sport', 'RDC', ['tatamis'], None, None, ''),
    ('SPORT-027', 'Salle de judo', 40, 'EXT', 'sport', 'RDC', ['tatamis'], None, None, ''),
    ('SPORT-028', 'Salle de musculation principale', 50, 'EXT', 'sport', 'RDC', ['machines', 'haltères'], None, None, ''),
    ('SPORT-029', 'Salle haltérophilie', 25, 'EXT', 'sport', 'RDC', ['barres', 'plateformes'], None, None, ''),

    # ── 6. Laboratoires pédagogiques ─────────────────────────────────
    ('LAB-010', 'Laboratoire Informatique 1', 35, 'LAB', 'lab', '1', ['pc', 'réseau'], None, None, ''),
    ('LAB-011', 'Laboratoire Informatique 2', 35, 'LAB', 'lab', '1', ['pc', 'réseau'], None, None, ''),
    ('LAB-012', 'Laboratoire Réseaux', 24, 'LAB', 'lab', '2', ['switch', 'routeurs', 'pc'], None, None, ''),
    ('LAB-013', 'Laboratoire IA', 20, 'LAB', 'lab', '2', ['gpu', 'workstations'], None, None, ''),
    ('LAB-014', 'Laboratoire Analyse vidéo', 18, 'LAB', 'lab', '2', ['stations_video'], None, None, ''),
    ('LAB-015', 'Laboratoire Biomécanique', 16, 'LAB', 'lab', '3', ['capteurs', 'mocap'], None, None, ''),
    ('LAB-016', 'Laboratoire Physiologie', 16, 'LAB', 'lab', '3', ['ergomètre', 'analyseurs'], None, None, ''),
    ('LAB-017', 'Laboratoire Psychologie', 20, 'LAB', 'lab', '3', ['tests_psy'], None, None, ''),
    ('LAB-018', 'Laboratoire Statistiques', 30, 'LAB', 'lab', '1', ['pc', 'spss', 'r'], None, None, ''),
    ('LAB-019', 'Laboratoire Recherche scientifique', 15, 'LAB', 'lab', '3', ['instruments_mesure'], None, None, ''),

    # ── 7. Espaces numériques ────────────────────────────────────────
    ('INF-010', 'Salle informatique A', 40, 'NUM', 'computer', '1', ['pc', 'wifi'], None, None, ''),
    ('INF-011', 'Salle informatique B', 40, 'NUM', 'computer', '1', ['pc', 'wifi'], None, None, ''),
    ('INF-012', 'Cyber étudiant', 50, 'NUM', 'computer', 'RDC', ['pc', 'imprimantes'], None, None, ''),
    ('INF-013', 'Centre e-learning campus', 45, 'NUM', 'computer', '1', ['pc', 'casques'], None, None, ''),
    ('SPEC-010', 'Studio MOOC', 12, 'NUM', 'specialized', 'RDC', ['cameras', 'fond_vert'], None, None, ''),
    ('INF-014', 'Salle réalité virtuelle', 16, 'NUM', 'computer', '2', ['casques_vr', 'stations'], None, None, ''),
    ('INF-015', 'Salle intelligence artificielle', 20, 'NUM', 'computer', '2', ['gpu', 'workstations'], None, None, ''),
    ('INF-016', 'Salle développement mobile', 24, 'NUM', 'computer', '2', ['pc', 'tablettes', 'emulateurs'], None, None, ''),
    ('INF-017', 'Salle cybersécurité', 20, 'NUM', 'computer', '2', ['lab_securite', 'pc'], None, None, ''),

    # ── 8. Espaces de recherche ──────────────────────────────────────
    ('RECH-001', 'Centre de recherche STAPS', 30, 'RECH', 'research', '1', ['bureaux', 'wifi'], None, None, ''),
    ('RECH-002', 'Centre de recherche STASE', 30, 'RECH', 'research', '1', ['bureaux', 'wifi'], None, None, ''),
    ('RECH-003', 'Centre innovation sportive', 25, 'RECH', 'research', '2', ['prototypage', 'wifi'], None, None, ''),
    ('RECH-004', 'Salle doctorants', 20, 'RECH', 'research', '2', ['bureaux', 'pc'], None, None, ''),
    ('RECH-005', 'Salle chercheurs', 15, 'RECH', 'research', '2', ['bureaux'], None, None, ''),
    ('RECH-006', 'Salle publications', 12, 'RECH', 'research', '1', ['archivage', 'pc'], None, None, ''),

    # ── 9. Bibliothèque ──────────────────────────────────────────────
    ('BIB-001', 'Salle lecture générale', 80, 'BIB', 'library', '1', ['rayonnages', 'wifi'], 5.3488, -3.9862, ''),
    ('BIB-002', 'Salle lecture numérique', 40, 'BIB', 'library', '1', ['pc', 'ebooks'], None, None, ''),
    ('BIB-003', 'Salle mémoire', 20, 'BIB', 'library', '2', ['archives_memoires'], None, None, ''),
    ('BIB-004', 'Salle thèses', 15, 'BIB', 'library', '2', ['archives_theses'], None, None, ''),
    ('BIB-005', 'Salle revues', 25, 'BIB', 'library', '1', ['revues_scientifiques'], None, None, ''),
    ('BIB-006', 'Salle audiovisuelle bibliothèque', 20, 'BIB', 'library', 'RDC', ['écrans', 'casques'], None, None, ''),
    ('BIB-007', 'Archives', 10, 'BIB', 'library', 'SS', ['archivage'], None, None, ''),

    # ── 10. Salles spécialisées ──────────────────────────────────────
    ('SPEC-020', 'Salle de langues', 30, 'SPEC', 'specialized', '1', ['lab_langues', 'casques'], None, None, ''),
    ('SPEC-021', 'Salle de communication campus', 35, 'SPEC', 'specialized', '1', ['sono', 'projecteur'], None, None, ''),
    ('SPEC-022', 'Salle audiovisuelle', 25, 'SPEC', 'specialized', '1', ['écrans', 'sono'], None, None, ''),
    ('SPEC-023', 'Salle audiovisuel sportif', 25, 'SPEC', 'specialized', '1', ['analyse_video'], None, None, ''),
    ('SPEC-024', 'Salle pédagogie', 30, 'SPEC', 'specialized', '2', ['matériel_pédagogique'], None, None, ''),
    ('SPEC-025', 'Salle innovation', 25, 'SPEC', 'specialized', '2', ['wifi', 'projecteur'], None, None, ''),
    ('SPEC-026', 'Salle entrepreneuriat campus', 30, 'SPEC', 'specialized', '2', ['wifi', 'projecteur'], None, None, ''),
    ('SPEC-027', 'Salle leadership', 25, 'SPEC', 'specialized', '2', ['projecteur'], None, None, ''),
    ('SPEC-028', 'Salle protocoles', 20, 'SPEC', 'specialized', 'RDC', ['sono'], None, None, ''),

    # ── 11. Espaces administratifs liés aux enseignements ────────────
    ('ADM-001', 'Direction des études', 8, 'ADM', 'admin', '1', ['bureaux'], None, None, ''),
    ('ADM-002', 'Service Scolarité', 12, 'ADM', 'admin', 'RDC', ['guichets', 'pc'], None, None, ''),
    ('ADM-003', 'Service Examens', 10, 'ADM', 'admin', '1', ['bureaux', 'coffre'], None, None, ''),
    ('ADM-004', 'Service Emplois du temps', 6, 'ADM', 'admin', '1', ['pc', 'planning'], None, None, ''),
    ('ADM-005', 'Service Stages', 8, 'ADM', 'admin', '1', ['bureaux'], None, None, ''),
    ('ADM-006', 'Service LMD', 8, 'ADM', 'admin', '1', ['bureaux', 'pc'], None, None, ''),
    ('ADM-007', 'Bureau enseignants', 20, 'ADM', 'admin', '2', ['bureaux', 'wifi'], None, None, ''),
    ('ADM-008', 'Bureau responsables pédagogiques', 10, 'ADM', 'admin', '2', ['bureaux'], None, None, ''),

    # ── 12. Espaces polyvalents ──────────────────────────────────────
    ('CONF-002', 'Salle de conférences', 120, 'POLY', 'conference', 'RDC', ['sono', 'projecteur', 'visioconférence'], None, None, ''),
    ('SEM-001', 'Salle des soutenances', 60, 'POLY', 'seminar', '1', ['projecteur', 'sono'], None, None, ''),
    ('SEM-002', 'Salle des conseils', 40, 'POLY', 'seminar', '1', ['table_reunion', 'projecteur'], None, None, ''),
    ('SEM-003', 'Salle de formation continue', 50, 'POLY', 'seminar', '1', ['projecteur', 'wifi'], None, None, ''),
    ('SEM-004', 'Salle de séminaires', 45, 'POLY', 'seminar', '2', ['projecteur'], None, None, ''),
    ('CONF-003', 'Salle des cérémonies', 300, 'POLY', 'conference', 'RDC', ['sono', 'éclairage_scène'], None, None, ''),

    # ── 13. Résidences pédagogiques ──────────────────────────────────
    ('RES-001', 'Dortoir Hommes', 120, 'RES', 'residence', '1-3', ['lits', 'sanitaires'], None, None, ''),
    ('RES-002', 'Dortoir Femmes', 120, 'RES', 'residence', '1-3', ['lits', 'sanitaires'], None, None, ''),
    ('RES-003', 'Salle d\'étude résidence', 40, 'RES', 'residence', 'RDC', ['tables', 'wifi'], None, None, ''),
    ('RES-004', 'Salle informatique résidence', 20, 'RES', 'computer', 'RDC', ['pc', 'wifi'], None, None, ''),
    ('RES-005', 'Salle TV résidence', 30, 'RES', 'residence', 'RDC', ['tv'], None, None, ''),
    ('RES-006', 'Salle de réunion résidence', 25, 'RES', 'residence', 'RDC', ['table_reunion'], None, None, ''),

    # ── 14. Espaces extérieurs campus ────────────────────────────────
    ('CAMP-001', 'Place d\'armes', 500, 'CAMPUS', 'outdoor', '', ['espace_ouvert'], 5.3470, -3.9870, ''),
    ('CAMP-002', 'Esplanade', 300, 'CAMPUS', 'outdoor', '', ['espace_ouvert'], None, None, ''),
    ('CAMP-003', 'Jardin pédagogique', 50, 'CAMPUS', 'outdoor', '', ['jardin'], None, None, ''),
    ('CAMP-004', 'Parcours sportif', 100, 'CAMPUS', 'outdoor', '', ['parcours_sante'], None, None, ''),
    ('CAMP-005', 'Aire de fitness extérieur', 40, 'CAMPUS', 'outdoor', '', ['agrès'], None, None, ''),
    ('CAMP-006', 'Parking enseignants', 80, 'CAMPUS', 'outdoor', '', ['places_parking'], None, None, ''),
    ('CAMP-007', 'Parking étudiants', 200, 'CAMPUS', 'outdoor', '', ['places_parking'], None, None, ''),

    # Alias historique (compatibilité seed démo)
    ('AMPHI-A', 'Amphithéâtre A (historique)', 200, 'ENSEPS', 'amphitheater', 'RDC', ['sono', 'projecteur'], 5.3478, -3.9865, 'Alias legacy — préférer AMP-001'),
]


def room_dicts():
    """Retourne la liste normalisée pour insertion DB."""
    result = []
    for row in CAMPUS_ROOMS:
        code, name, capacity, building, room_type, floor, equipment, lat, lng, notes = row
        result.append({
            'code': code,
            'name': name,
            'capacity': capacity,
            'building': building,
            'room_type': room_type,
            'floor': floor or '',
            'equipment': equipment or [],
            'latitude': lat,
            'longitude': lng,
            'notes': notes or '',
            'status': 'available',
            'is_active': True,
        })
    return result
