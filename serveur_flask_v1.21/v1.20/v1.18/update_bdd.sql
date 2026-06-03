-- Mise à jour BDD pour v1.18 — Ajout utilisateurs de test
-- Lancer : sudo mysql samv2 < update_bdd.sql

INSERT IGNORE INTO `user` (`login_user`, `mdph_user`, `role_user`) VALUES
    ('technicien', 'tech2026', 'technicien'),
    ('superviseur', 'super2026', 'superviseur');
