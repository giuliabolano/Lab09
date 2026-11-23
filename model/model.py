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
        # questo metodo serve a collegare le escursioni ai rispettivi punti di interesse in memoria, tramite la tabella di relazione
        # N:N presente nel database
        #prendiamo le info dal DAO
        #per ogni riga di relazione, recupera l'escursione e il punto di interesse delle mappe e aggiorna i rispettivi
        # set bidirezionali in modo da sapere quali punti di interesse appartengono a un'escursione e viceversa

        #interroga il database tramite il DAO per recuperare tutte le associazioni tra le escursioni e i punti di interesse
        #salvando il risultato nella variabile "relazioni"
        relazioni = EscursioneDAO.get_escursioni_punti_interesse()

        #iteriamo sulle relazioni per popolare i set reciproci
        if relazioni is not None: #controllo sicurezza, verifica che il database abbia restituito dati e che relazioni non sia vuoto
            for relazione in relazioni: #scorre tutte le relazioni
                id_escursione = relazione["id_escursione"] #estrae dal dizionario della singola relazione l'identificativo (id)
                # dell'escursione e lo memorizza nella variabile id_escursione
                id_punto_interesse = relazione["id_punto_interesse"] #idem

                #verifica che l'id dell'escursione esista nel dizionario globale self.escursione_map e cuguale il punto di interesse
                if id_escursione in self.escursioni_map and id_punto_interesse in self.punti_interesse_map:
                    #a questo punto prende l'oggetto escursione/punto interesse all'interno del dizionario usando la sua chiave id e lo assegna alla variabile
                    escursione= self.escursioni_map[id_escursione]
                    punto_interesse= self.punti_interesse_map[id_punto_interesse]

                    #creazione collegamento bidirezionale:
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
        self._valore_ottimo = -1 #valore sentinella basso così che qualsiasi punteggio reale calcolato dopo lo batta

        #gestione dei valori di default se non impostati dall'utente
        if max_budget is None: #controlla se l'utente non ha inserito un budget o un max giorni
            self._max_budget= float("inf") #in quel caso non c'è limite di spesa o restrizioni di tempo
        else:
            self._max_budget = max_budget #sennò viene impostato quel valore inserito

        if max_giorni is None:
            self._max_giorni = float("inf")
        else:
            self._max_giorni = max_giorni

        # crea una lista vuota in cui andrà a memorizzaresoltanto le escursioni disponibili che appartengono esclusivamente al parco selezionato
        self._escursioni_parco= []
        for escursione in self.escursioni_map.values(): #scorre tutte le escursioni esistenti
            if escursione.id_parco == id_parco: #controlla se l'escursione corrente appartiene al parco selezionato dall'utente
                self._escursioni_parco.append(escursione) #se è così la aggiunge alla lista

        #chiamo la funzione ricorsiva
        #lista vuota che servirà a costruire e testare le varie combinazioni di escursioni durante la ricorsione
        parziale= []
        #fa partire l'algoritmo di ricerca ricorsiva (backtracking) passando quegli argomenti
        #prima escursione, lista vuota delle escursioni scelte, durata accumulata, costo accumulato, punteggio accumulato
        self._ricorsione(0, parziale, 0, 0.0, 0, set()) #set evita duplicati per tenere traccia dei punti di interesse già visitati

        return self._pacchetto_ottimo, self._costo, self._valore_ottimo
    #una volta che la ricorsione ha terminato di esplorare tutte le combinazioni possibili trovando la migliore, questo comando
    # restituisce il pacchetto ottimo trovato, il suo costo totale e il suo valore complessivo di gradimento




    def _ricorsione(self, start_index: int, pacchetto_parziale: list, durata_corrente: int, costo_corrente: float, valore_corrente: int, punti_usati: set):
        """ Algoritmo di ricorsione che deve trovare il pacchetto che massimizza il voto complessivo dei visitatori"""

        # 1) valutazione della soluzione corrente (salviamo la migliore)
        #controlla se il punteggio della combinazione appena trovata è maggiore (voto più alto) di quella migliore che avevamo salvato
        if valore_corrente > self._valore_ottimo:
            self._valore_ottimo = valore_corrente #se sì si salva quello nuovo come nuovo migliore
            self._pacchetto_ottimo = pacchetto_parziale.copy() #copia la lista del pacchetto corrente per evitare riferimenti di memoria non voluti
            self._costo = costo_corrente # e si registra il costo totale associato

        # 2) condizione di terminazione: se abbiamo esaminato tutte le escursioni del parco
        # se l'indice ha superato o eguagliato il numero totale delle escursioni disponibili per quel parco, la ricerca si interrompe
        if start_index >= len(self._escursioni_parco):
            return

        # 3) seleziona l'escursione corrente dall'elenco del parco in base a all'indice di avanzamento della ricorsione
        escursione_corrente = self._escursioni_parco[start_index]

        # Verifichiamo se l'escursione ha punti di interesse già usati nel pacchetto
        #esegue un controllo di unicità: itera sui punti di interesse associati all'escursione corrente per verificare se qualcuno di essi è
        # già presente nell'insieme punti_usati, se si rivela una duplicazione (sovrapposzione=True) si interrompe prima il ciclo
        sovrapposizione = False
        for p in escursione_corrente.punti_interesse:
            if p.id in punti_usati:
                sovrapposizione = True
                break

        # 4) controllo dei vincoli (durata, budget e unicità dei punti di interesse)
        # controlla simultaneamente che l'aggiunta dell'escursione non violi il limite massimo dei giorni, il budget economico massimo e che non crei
        # conflitti sui punti di interesse
        if (durata_corrente + escursione_corrente.durata_giorni <= self._max_giorni) and \
                (costo_corrente + escursione_corrente.costo <= self._max_budget) and \
                (not sovrapposizione):

            #A: Includiamo l'escursione nella soluzione parziale
            pacchetto_parziale.append(escursione_corrente)

            # Aggiorniamo i punti usati e il valore corrente aggiungendo i nuovi punti di interesse
            #crea una copia aggiornata dell'insieme dei punti utilizzati e ricalcola il gradimento cumulativo sommando i voti
            # dei nuovi punti di interesse introdotti da questa escursione
            # in sostanza mentre si prova ad aggiungere questa nuova escursione, aggiorniamo la lista dei posti visti e sommiamo
            # i nuovi punti di gradimento (ogni punto di interesse ha un voto e questi vengono sommati) al totale
            # così da sapere quanto vale quella combinazione
            nuovi_punti_usati = punti_usati.copy()
            nuovo_valore = valore_corrente
            for p in escursione_corrente.punti_interesse:
                nuovi_punti_usati.add(p.id)
                nuovo_valore += p.voto_visitatori

            # Chiamata ricorsiva includendo l'escursione
            #effettua la chiamata ricorsiva passando all'escursione successiva (start_index +1) e aggiornando i contatori di durata,
            # costo, valore e l'insieme dei punti di interesse
            self._ricorsione(start_index + 1, pacchetto_parziale,
                             durata_corrente + escursione_corrente.durata_giorni,
                             costo_corrente + escursione_corrente.costo,
                             nuovo_valore, nuovi_punti_usati)

            # Backtracking (rimuoviamo l'escursione)
            #una volta completata l'esplorazione di quel ramo, rimuove l'ultima escursione aggiunta per consentire di valutare  percorsi alternativi
            pacchetto_parziale.pop()

        #B: Saltiamo l'escursione corrente
        # gestisce l'alternativa in cui si sceglie di saltare l'escursione corrente: la ricorsione avanza all'indice successivo
        # senza modificare la composizione e i totali del pacchetto parziale
        self._ricorsione(start_index + 1, pacchetto_parziale,
                         durata_corrente, costo_corrente,
                         valore_corrente, punti_usati)

