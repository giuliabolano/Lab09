from database import escursione_DAO
from database.parco_DAO import ParcoDAO
from database.escursione_DAO import EscursioneDAO
from database.punto_interesse_DAO import PuntoInteresseDAO
from model.escursione import Escursione


class Model:
    def __init__(self):
        self.escursioni_map = {} # Mappa ID escursione -> oggetti Escursione
        self.punti_interesse_map = {} # Mappa ID punto di interesse -> oggetti PuntoInteresse

        self._pacchetto_ottimo = []
        self._valore_ottimo: int = -1
        self._costo = 0

        # TODO: Aggiungere eventuali altri attributi

        # Caricamento
        self.load_escursioni()
        self.load_punti_interesse()
        self.load_relazioni()

    @staticmethod
    def load_parchi():
        """ Restituisce tutti i parchi disponibili """
        return ParcoDAO.get_parchi()

    def load_escursioni(self):
        """ Carica tutte le escursioni in un dizionario [id, Escursione]"""
        self.escursioni_map = EscursioneDAO.get_escursioni()

    def load_punti_interesse(self):
        """ Carica tutti i punti di interesse in un dizionario [id, PuntoInteresse]"""
        self.punti_interesse_map = PuntoInteresseDAO.get_punti_interesse()

    def load_relazioni(self):
        """
            Interroga il database per ottenere tutte le relazioni fra escursioni e punti di interesse e salvarle nelle strutture dati
            Collega escursione <-> punti di interesse.
            --> Ogni Escursione ha un set di PuntoInteresse.
            --> Ogni PuntoInteresse ha un set di Escursioni.
        """
        # questo metodo serve a collegare le escursioni ai rispettivi punti di interesse tramite la tabella di relazione
        # N:N presente nel database
        #prendiamo le info dal DAO
        relazioni = EscursioneDAO.get_escursioni_punti_interesse()

        #iteriamo sulle relazioni per popolare i set reciproci
        if relazioni is not None:
            for relazione in relazioni:
                id_escursione = relazione["id_escursione"]
                id_punto_interesse = relazione["id_punto_interesse"]

                #verifichiamo che entrambi gli oggetti esistano nelle mappe
                if id_escursione in self.escursioni_map and id_punto_interesse in self.punti_interesse_map:
                    escursione= self.escursioni_map[id_escursione]
                    punto_interesse= self.punti_interesse_map[id_punto_interesse]

                    #aggiungiamo il punto di interesse all'escursione
                    escursione.punti_interesse.add(punto_interesse)
                    #aggiungiamo l'escursione al punto di interesse
                    punto_interesse.escursioni.add(escursione)



    def genera_pacchetto(self, id_parco: str, max_giorni: int = None, max_budget: float = None):
        """
        Calcola il pacchetto di escursioni ottimale per un parco rispettando i vincoli di durata, budget e punti di interesse unici.
        :param id_parco: id del parco
        :param max_giorni: numero massimo di giorni (può essere None --> nessun limite)
        :param max_budget: costo massimo del pacchetto (può essere None --> nessun limite)

        :return: self._pacchetto_ottimo (una lista di oggetti Escursione)
        :return: self._costo (il costo del pacchetto)
        :return: self._valore_ottimo (il voto complessivo dei visitatori per il pacchetto)
        """
        self._pacchetto_ottimo = []
        self._costo = 0
        self._valore_ottimo = -1

        #gestione dei valori di default se non impostati dall'utente
        if max_budget is not None:
            self._max_budget= float("inf")
        if max_giorni is not None:
            self._max_giorni = float("inf")

        # filtrare le escursioni disponibiliche appartengono esclusivamente al parco selezionato
        self._escursioni_parco= []
        for escursione in self.escursioni_map.values():
            if escursione.id_parco == id_parco:
                self._escursioni_parco.append(escursione)

        #chiamo la funzione ricorsiva
        parziale= []
        self._ricorsione(0, parziale, 0, 0.0, 0, set())

        return self._pacchetto_ottimo, self._costo, self._valore_ottimo




    def _ricorsione(self, start_index: int, pacchetto_parziale: list, durata_corrente: int, costo_corrente: float, valore_corrente: int, punti_usati: set):
        """ Algoritmo di ricorsione che deve trovare il pacchetto che massimizza il voto complessivo dei visitatori"""

        # 1. Valutazione della soluzione corrente (salviamo la migliore)
        if valore_corrente > self._valore_ottimo:
            self._valore_ottimo = valore_corrente
            self._pacchetto_ottimo = pacchetto_parziale.copy()
            self._costo = costo_corrente

        # 2. Condizione di terminazione: se abbiamo esaminato tutte le escursioni del parco
        if start_index >= len(self._escursioni_parco):
            return

        # 3. Prendiamo l'escursione corrente in base a start_index
        escursione_corrente = self._escursioni_parco[start_index]

        # Verifichiamo se l'escursione ha punti di interesse già usati nel pacchetto
        sovrapposizione = False
        for p in escursione_corrente.punti_interesse:
            if p.id in punti_usati:
                sovrapposizione = True
                break

        # 4. Controllo dei vincoli (durata, budget e unicità dei punti di interesse)
        if (durata_corrente + escursione_corrente.durata_giorni <= self._max_giorni) and \
                (costo_corrente + escursione_corrente.costo <= self._max_budget) and \
                (not sovrapposizione):

            # --- SCELTA A: Includiamo l'escursione ---
            pacchetto_parziale.append(escursione_corrente)

            # Aggiorniamo i punti usati e il valore corrente aggiungendo i nuovi punti di interesse
            nuovi_punti_usati = punti_usati.copy()
            nuovo_valore = valore_corrente
            for p in escursione_corrente.punti_interesse:
                nuovi_punti_usati.add(p.id)
                nuovo_valore += p.voto_visitatori  # Assicurati che l'attributo del voto sia corretto (es. voto_visitatori)

            # Chiamata ricorsiva includendo l'escursione
            self._ricorsione(start_index + 1, pacchetto_parziale,
                             durata_corrente + escursione_corrente.durata_giorni,
                             costo_corrente + escursione_corrente.costo,
                             nuovo_valore, nuovi_punti_usati)

            # Backtracking (rimuoviamo l'escursione)
            pacchetto_parziale.pop()

        # --- SCELTA B: Saltiamo l'escursione corrente ---
        self._ricorsione(start_index + 1, pacchetto_parziale,
                         durata_corrente, costo_corrente,
                         valore_corrente, punti_usati)

