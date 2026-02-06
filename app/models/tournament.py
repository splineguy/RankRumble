"""
Tournament manager for Sweet Sixteen double-elimination brackets.
"""
import random
from typing import Optional

from app.models.storage import generate_id, get_timestamp


# Standard 16-seed bracket matchups (1v16, 8v9, 5v12, 4v13, 6v11, 3v14, 7v10, 2v15)
SEED_MATCHUPS = [
    (0, 15), (7, 8), (4, 11), (3, 12),
    (5, 10), (2, 13), (6, 9), (1, 14)
]

# Defines the play order for the entire tournament.
# Each entry: (bracket_type, round_index) where bracket_type is 'w', 'l', 'gf', or 'reset'
PLAY_ORDER = [
    ('w', 0),   # WB R1: 8 matches
    ('l', 0),   # LB R1: 4 matches (WB R1 losers paired)
    ('w', 1),   # WB R2: 4 matches
    ('l', 1),   # LB R2: 4 matches (LB R1 winners vs WB R2 losers)
    ('l', 2),   # LB R3: 2 matches (LB R2 winners paired)
    ('w', 2),   # WB R3/Semis: 2 matches
    ('l', 3),   # LB R4: 2 matches (LB R3 winners vs WB R3 losers)
    ('l', 4),   # LB R5: 1 match (LB semifinal)
    ('w', 3),   # WB R4/Final: 1 match
    ('l', 5),   # LB R6: 1 match (LB final: LB R5 winner vs WB R4 loser)
    ('gf', 0),  # Grand Final
    ('reset', 0),  # Reset match (conditional)
]


def _create_match(item_a_id=None, item_b_id=None):
    """Create a new match dict."""
    return {
        'id': generate_id('match'),
        'item_a_id': item_a_id,
        'item_b_id': item_b_id,
        'winner_id': None,
        'loser_id': None,
        'battle_id': None,
    }


class TournamentManager:
    """Manages double-elimination tournament brackets."""

    def __init__(self, project_manager):
        self.project_manager = project_manager

    def create_tournament(self, user_id: str, project_id: str,
                          item_ids: list, name: str = None) -> Optional[dict]:
        """
        Create a new 16-item double-elimination tournament.

        Items are seeded by current ELO rating (highest = seed 1).
        """
        project = self.project_manager.get_project(user_id, project_id)
        if not project:
            return None

        if len(item_ids) != 16:
            return None

        # Verify all items exist
        for item_id in item_ids:
            if item_id not in project['items']:
                return None

        # Seed by current ELO (descending)
        items_with_rating = [
            (item_id, project['items'][item_id]['rating'])
            for item_id in item_ids
        ]
        items_with_rating.sort(key=lambda x: x[1], reverse=True)
        seeding = [item_id for item_id, _ in items_with_rating]

        # Build winners bracket R1 from seeding
        wb_r1 = []
        for seed_a, seed_b in SEED_MATCHUPS:
            wb_r1.append(_create_match(seeding[seed_a], seeding[seed_b]))

        # Build empty rounds for rest of winners bracket
        wb_r2 = [_create_match() for _ in range(4)]
        wb_r3 = [_create_match() for _ in range(2)]
        wb_r4 = [_create_match() for _ in range(1)]

        # Build empty losers bracket rounds
        lb_r1 = [_create_match() for _ in range(4)]  # 8 WB R1 losers → 4 matches
        lb_r2 = [_create_match() for _ in range(4)]  # LB R1 winners vs WB R2 losers
        lb_r3 = [_create_match() for _ in range(2)]  # LB R2 winners paired
        lb_r4 = [_create_match() for _ in range(2)]  # LB R3 winners vs WB R3 losers
        lb_r5 = [_create_match() for _ in range(1)]  # LB semifinal
        lb_r6 = [_create_match() for _ in range(1)]  # LB final

        tournament = {
            'id': generate_id('tourn'),
            'name': name or f"Sweet Sixteen #{len(project.get('tournaments', {})) + 1}",
            'created_at': get_timestamp(),
            'status': 'in_progress',
            'participants': item_ids,
            'seeding': seeding,
            'winners_bracket': [wb_r1, wb_r2, wb_r3, wb_r4],
            'losers_bracket': [lb_r1, lb_r2, lb_r3, lb_r4, lb_r5, lb_r6],
            'grand_final': {
                'match': _create_match(),
                'reset_match': None,
            },
            'champion_id': None,
            'results': None,
            'match_count': 0,
            'total_matches': 30,  # 8+4+4+4+2+2+2+1+1+1+1 = 30 (max with reset: 31)
        }

        # Store in project
        if 'tournaments' not in project:
            project['tournaments'] = {}
        project['tournaments'][tournament['id']] = tournament
        project['updated_at'] = get_timestamp()
        self.project_manager._save_project(user_id, project_id, project)

        return tournament

    def get_tournament(self, user_id: str, project_id: str,
                       tournament_id: str) -> Optional[dict]:
        """Get a tournament by ID."""
        project = self.project_manager.get_project(user_id, project_id)
        if not project:
            return None
        return project.get('tournaments', {}).get(tournament_id)

    def list_tournaments(self, user_id: str, project_id: str) -> list:
        """List all tournaments for a project."""
        project = self.project_manager.get_project(user_id, project_id)
        if not project:
            return []
        tournaments = list(project.get('tournaments', {}).values())
        tournaments.sort(key=lambda t: t['created_at'], reverse=True)
        return tournaments

    def get_next_match(self, tournament: dict, project: dict) -> Optional[dict]:
        """
        Find the next unplayed match following the correct play order.

        Returns dict with match info and context, or None if tournament is complete.
        """
        if tournament['status'] == 'completed':
            return None

        for bracket_type, round_idx in PLAY_ORDER:
            if bracket_type == 'w':
                round_matches = tournament['winners_bracket'][round_idx]
                for match_idx, match in enumerate(round_matches):
                    if (match['winner_id'] is None and
                            match['item_a_id'] is not None and
                            match['item_b_id'] is not None):
                        round_names = ['Round 1', 'Quarterfinals', 'Semifinals', 'Final']
                        return {
                            'match': match,
                            'bracket': 'winners',
                            'bracket_label': 'Winners Bracket',
                            'round_idx': round_idx,
                            'round_name': round_names[round_idx],
                            'match_idx': match_idx,
                            'match_number': match_idx + 1,
                            'total_in_round': len(round_matches),
                            'item_a': project['items'].get(match['item_a_id']),
                            'item_b': project['items'].get(match['item_b_id']),
                        }

            elif bracket_type == 'l':
                round_matches = tournament['losers_bracket'][round_idx]
                for match_idx, match in enumerate(round_matches):
                    if (match['winner_id'] is None and
                            match['item_a_id'] is not None and
                            match['item_b_id'] is not None):
                        lb_round_names = [
                            'Round 1', 'Round 2', 'Round 3',
                            'Round 4', 'Semifinal', 'Final'
                        ]
                        return {
                            'match': match,
                            'bracket': 'losers',
                            'bracket_label': 'Losers Bracket',
                            'round_idx': round_idx,
                            'round_name': lb_round_names[round_idx],
                            'match_idx': match_idx,
                            'match_number': match_idx + 1,
                            'total_in_round': len(round_matches),
                            'item_a': project['items'].get(match['item_a_id']),
                            'item_b': project['items'].get(match['item_b_id']),
                        }

            elif bracket_type == 'gf':
                match = tournament['grand_final']['match']
                if (match['winner_id'] is None and
                        match['item_a_id'] is not None and
                        match['item_b_id'] is not None):
                    return {
                        'match': match,
                        'bracket': 'grand_final',
                        'bracket_label': 'Grand Final',
                        'round_idx': 0,
                        'round_name': 'Grand Final',
                        'match_idx': 0,
                        'match_number': 1,
                        'total_in_round': 1,
                        'item_a': project['items'].get(match['item_a_id']),
                        'item_b': project['items'].get(match['item_b_id']),
                    }

            elif bracket_type == 'reset':
                reset = tournament['grand_final'].get('reset_match')
                if reset and reset['winner_id'] is None:
                    return {
                        'match': reset,
                        'bracket': 'reset',
                        'bracket_label': 'True Final',
                        'round_idx': 0,
                        'round_name': 'True Final',
                        'match_idx': 0,
                        'match_number': 1,
                        'total_in_round': 1,
                        'item_a': project['items'].get(reset['item_a_id']),
                        'item_b': project['items'].get(reset['item_b_id']),
                    }

        return None

    def submit_tournament_match(self, user_id: str, project_id: str,
                                tournament_id: str, match_id: str,
                                winner_side: str) -> Optional[dict]:
        """
        Submit a tournament match result.

        Args:
            winner_side: 'a' or 'b' (which side won)

        Returns:
            Battle record from the ELO system, or None on error.
        """
        project = self.project_manager.get_project(user_id, project_id)
        if not project:
            return None

        tournament = project.get('tournaments', {}).get(tournament_id)
        if not tournament or tournament['status'] == 'completed':
            return None

        # Find the match
        match, location = self._find_match(tournament, match_id)
        if not match:
            return None

        # Determine winner/loser
        if winner_side == 'a':
            result = 'a_wins'
            match['winner_id'] = match['item_a_id']
            match['loser_id'] = match['item_b_id']
        else:
            result = 'b_wins'
            match['winner_id'] = match['item_b_id']
            match['loser_id'] = match['item_a_id']

        # Submit to ELO system
        battle_record = self.project_manager.submit_battle(
            user_id=user_id,
            project_id=project_id,
            item_a_id=match['item_a_id'],
            item_b_id=match['item_b_id'],
            result=result
        )

        if battle_record:
            match['battle_id'] = battle_record['id']

        # Re-load project since submit_battle saved it
        project = self.project_manager.get_project(user_id, project_id)
        tournament = project['tournaments'][tournament_id]

        # Re-find match to update it with winner/loser
        match_ref, _ = self._find_match(tournament, match_id)
        match_ref['winner_id'] = match['winner_id']
        match_ref['loser_id'] = match['loser_id']
        match_ref['battle_id'] = match.get('battle_id')

        tournament['match_count'] = tournament.get('match_count', 0) + 1

        # Advance bracket
        self._advance_bracket(tournament, location, match)

        # Check if tournament is complete
        if self._is_complete(tournament):
            tournament['status'] = 'completed'
            # Determine champion
            gf = tournament['grand_final']
            reset = gf.get('reset_match')
            if reset and reset['winner_id']:
                tournament['champion_id'] = reset['winner_id']
                runner_up = reset['loser_id']
            else:
                tournament['champion_id'] = gf['match']['winner_id']
                runner_up = gf['match']['loser_id']

            tournament['results'] = {
                '1st': tournament['champion_id'],
                '2nd': runner_up,
            }

        project['updated_at'] = get_timestamp()
        self.project_manager._save_project(user_id, project_id, project)

        return battle_record

    def _find_match(self, tournament: dict, match_id: str):
        """Find a match by ID and return (match, location_tuple)."""
        # Check winners bracket
        for r_idx, round_matches in enumerate(tournament['winners_bracket']):
            for m_idx, match in enumerate(round_matches):
                if match['id'] == match_id:
                    return match, ('w', r_idx, m_idx)

        # Check losers bracket
        for r_idx, round_matches in enumerate(tournament['losers_bracket']):
            for m_idx, match in enumerate(round_matches):
                if match['id'] == match_id:
                    return match, ('l', r_idx, m_idx)

        # Check grand final
        if tournament['grand_final']['match']['id'] == match_id:
            return tournament['grand_final']['match'], ('gf', 0, 0)

        # Check reset match
        reset = tournament['grand_final'].get('reset_match')
        if reset and reset['id'] == match_id:
            return reset, ('reset', 0, 0)

        return None, None

    def _advance_bracket(self, tournament: dict, location: tuple, match: dict):
        """
        Advance the bracket after a match is completed.

        Moves the winner forward and the loser to the losers bracket (if from WB).
        """
        bracket_type, round_idx, match_idx = location
        winner_id = match['winner_id']
        loser_id = match['loser_id']

        if bracket_type == 'w':
            self._advance_winners_bracket(tournament, round_idx, match_idx, winner_id, loser_id)
        elif bracket_type == 'l':
            self._advance_losers_bracket(tournament, round_idx, match_idx, winner_id)
        elif bracket_type == 'gf':
            self._handle_grand_final(tournament, match)
        # Reset match: no advancement needed, _is_complete will handle it

    def _advance_winners_bracket(self, tournament, round_idx, match_idx, winner_id, loser_id):
        """Advance winner in WB and send loser to LB."""
        wb = tournament['winners_bracket']
        lb = tournament['losers_bracket']

        # Advance winner to next WB round
        if round_idx < 3:  # Not the WB final yet
            next_match_idx = match_idx // 2
            next_match = wb[round_idx + 1][next_match_idx]
            if match_idx % 2 == 0:
                next_match['item_a_id'] = winner_id
            else:
                next_match['item_b_id'] = winner_id
        else:
            # WB Final winner goes to Grand Final as item_a (WB champion)
            tournament['grand_final']['match']['item_a_id'] = winner_id

        # Send loser to appropriate losers bracket round
        if round_idx == 0:
            # WB R1 losers → LB R1 (paired: losers 0,1→match 0, losers 2,3→match 1, etc.)
            lb_match_idx = match_idx // 2
            lb_match = lb[0][lb_match_idx]
            if match_idx % 2 == 0:
                lb_match['item_a_id'] = loser_id
            else:
                lb_match['item_b_id'] = loser_id

        elif round_idx == 1:
            # WB R2 losers → LB R2 as item_b (face LB R1 winners)
            lb[1][match_idx]['item_b_id'] = loser_id

        elif round_idx == 2:
            # WB R3 (Semis) losers → LB R4 as item_b (face LB R3 winners)
            lb[3][match_idx]['item_b_id'] = loser_id

        elif round_idx == 3:
            # WB Final loser → LB R6 as item_b (face LB R5 winner)
            lb[5][0]['item_b_id'] = loser_id

    def _advance_losers_bracket(self, tournament, round_idx, match_idx, winner_id):
        """Advance winner within the losers bracket."""
        lb = tournament['losers_bracket']

        if round_idx == 0:
            # LB R1 winners → LB R2 as item_a
            lb[1][match_idx]['item_a_id'] = winner_id

        elif round_idx == 1:
            # LB R2 winners → LB R3 (paired: winners 0,1→match 0, etc.)
            next_match_idx = match_idx // 2
            next_match = lb[2][next_match_idx]
            if match_idx % 2 == 0:
                next_match['item_a_id'] = winner_id
            else:
                next_match['item_b_id'] = winner_id

        elif round_idx == 2:
            # LB R3 winners → LB R4 as item_a
            lb[3][match_idx]['item_a_id'] = winner_id

        elif round_idx == 3:
            # LB R4 winners → LB R5 (paired)
            next_match_idx = match_idx // 2
            next_match = lb[4][next_match_idx]
            if match_idx % 2 == 0:
                next_match['item_a_id'] = winner_id
            else:
                next_match['item_b_id'] = winner_id

        elif round_idx == 4:
            # LB R5 winner → LB R6 as item_a
            lb[5][0]['item_a_id'] = winner_id

        elif round_idx == 5:
            # LB Final winner → Grand Final as item_b (LB champion)
            tournament['grand_final']['match']['item_b_id'] = winner_id

    def _handle_grand_final(self, tournament, match):
        """Handle grand final result — create reset match if LB champion wins."""
        gf = tournament['grand_final']
        wb_champion_id = gf['match']['item_a_id']

        if match['winner_id'] != wb_champion_id:
            # LB champion won — need a reset match
            gf['reset_match'] = _create_match(
                item_a_id=wb_champion_id,
                item_b_id=match['winner_id']
            )
            tournament['total_matches'] = 31

    def _is_complete(self, tournament: dict) -> bool:
        """Check if the tournament is complete."""
        gf = tournament['grand_final']

        # Grand final not played yet
        if gf['match']['winner_id'] is None:
            return False

        # If WB champion won grand final, tournament is done
        wb_champion_id = gf['match']['item_a_id']
        if gf['match']['winner_id'] == wb_champion_id:
            return True

        # LB champion won — check if reset match exists and is complete
        reset = gf.get('reset_match')
        if reset and reset['winner_id'] is not None:
            return True

        return False

    def get_bracket_display(self, tournament: dict, project: dict) -> dict:
        """
        Build a display-friendly version of the bracket with item names.
        """
        def enrich_match(match):
            """Add item names to a match."""
            result = dict(match)
            result['item_a_name'] = ''
            result['item_b_name'] = ''
            result['winner_name'] = ''
            if match['item_a_id'] and match['item_a_id'] in project['items']:
                result['item_a_name'] = project['items'][match['item_a_id']]['name']
            if match['item_b_id'] and match['item_b_id'] in project['items']:
                result['item_b_name'] = project['items'][match['item_b_id']]['name']
            if match['winner_id'] and match['winner_id'] in project['items']:
                result['winner_name'] = project['items'][match['winner_id']]['name']
            return result

        wb_display = []
        for round_matches in tournament['winners_bracket']:
            wb_display.append([enrich_match(m) for m in round_matches])

        lb_display = []
        for round_matches in tournament['losers_bracket']:
            lb_display.append([enrich_match(m) for m in round_matches])

        gf_display = {
            'match': enrich_match(tournament['grand_final']['match']),
            'reset_match': None,
        }
        if tournament['grand_final'].get('reset_match'):
            gf_display['reset_match'] = enrich_match(tournament['grand_final']['reset_match'])

        champion_name = ''
        if tournament['champion_id'] and tournament['champion_id'] in project['items']:
            champion_name = project['items'][tournament['champion_id']]['name']

        return {
            'tournament': tournament,
            'winners_bracket': wb_display,
            'losers_bracket': lb_display,
            'grand_final': gf_display,
            'champion_name': champion_name,
            'match_count': tournament.get('match_count', 0),
            'total_matches': tournament.get('total_matches', 30),
        }
