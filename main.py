import sys
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QPlainTextEdit, \
QLabel, QFileDialog, QPushButton, QRadioButton, QButtonGroup, QTextEdit, QMessageBox, QListWidget, QListWidgetItem, \
QComboBox, QTableWidget, QTableWidgetItem
from PyQt5.QtGui import QFont, QColor, QPalette, QTextLayout, QGuiApplication
from PyQt5.QtCore import Qt, pyqtSlot, QStringListModel, QCoreApplication, QObject, pyqtSignal, QRect
from PyQt5.QtGui import *
from time import sleep
from collections import defaultdict
import re
import win32.win32api as w32
# import win32.win32con as win32con
import datetime
import ctypes
from register import Register
from commend import PopUpWindow


class Stream(QObject):
    newText = pyqtSignal(str)

    def write(self, text):
        self.newText.emit(str(text))

    def flush(self):
        pass


class Application(QMainWindow, QWidget):
    def __init__(self, parent=None):
        super(Application, self).__init__(parent)
        self.title = "Simulator"
        screen_width = w32.GetSystemMetrics(0)
        screen_height = w32.GetSystemMetrics(1)
        self.width = 945
        self.height = 570
        self.left = (screen_width - self.width)/2
        self.top = -30+(screen_height-self.height)/2
        self.form_widget = None
        self.regA = Register("AX")
        self.regB = Register("BX")
        self.regC = Register("CX")
        self.regD = Register("DX")
        self.program_code = QPlainTextEdit(self)
        self.console = QPlainTextEdit(self)
        self.mode = -1
        self.help_bios = None
        self.step = False
        self.pattern1 = re.compile(r"\d{1,3}\s\D{3}\s\S{2},\S{2}")
        self.pattern2 = re.compile(r"\d{1,3}\s\D{3}\s\S{2},#\d{1,3}")
        self.pattern3 = re.compile(r"\d{1,3}\sINT\S{2}")
        self.pattern4 = re.compile(r"\d{1,3}\s\D{3,4}\s\S{2}")
        self.stack = []
        self.max_stack = 15
        self.stack_pointer = 0
        self.initWindow()

        sys.stdout = Stream(newText=self.onUpdateText)

    def initWindow(self):
        self.setWindowTitle(self.title)
        self.setStyleSheet("background-color: #808080;")
        self.setFixedSize(self.width, self.height)
        self.move(self.left, self.top)
        self.setFocusPolicy(Qt.StrongFocus)
        self.initWidgets()
        self.show()

    def help_action(self):
        self.choose_BIOS = QTableWidget(11, 3)
        self.choose_BIOS.setItem(0, 0, QTableWidgetItem("Przerwanie"))
        self.choose_BIOS.setItem(0, 1, QTableWidgetItem("Funkcja"))
        self.choose_BIOS.setItem(0, 2, QTableWidgetItem("Opis"))

        # przerwania
        self.choose_BIOS.setItem(1, 0, QTableWidgetItem("INT 21"))
        self.choose_BIOS.setItem(2, 0, QTableWidgetItem("INT 21"))
        self.choose_BIOS.setItem(3, 0, QTableWidgetItem("INT 21"))
        self.choose_BIOS.setItem(4, 0, QTableWidgetItem("INT 21"))

        self.choose_BIOS.setItem(5, 0, QTableWidgetItem("INT 10"))
        self.choose_BIOS.setItem(6, 0, QTableWidgetItem("INT 10"))

        self.choose_BIOS.setItem(7, 0, QTableWidgetItem("INT 1A"))
        self.choose_BIOS.setItem(8, 0, QTableWidgetItem("INT 1A"))
        self.choose_BIOS.setItem(9, 0, QTableWidgetItem("INT 1A"))
        self.choose_BIOS.setItem(10, 0, QTableWidgetItem("INT 1A"))

        # funkcje
        self.choose_BIOS.setItem(1, 1, QTableWidgetItem("00h"))
        self.choose_BIOS.setItem(2, 1, QTableWidgetItem("01h"))
        self.choose_BIOS.setItem(3, 1, QTableWidgetItem("02h"))
        self.choose_BIOS.setItem(4, 1, QTableWidgetItem("36h"))

        self.choose_BIOS.setItem(5, 1, QTableWidgetItem("02h"))
        self.choose_BIOS.setItem(6, 1, QTableWidgetItem("03h"))

        self.choose_BIOS.setItem(7, 1, QTableWidgetItem("02h"))
        self.choose_BIOS.setItem(8, 1, QTableWidgetItem("03h"))
        self.choose_BIOS.setItem(9, 1, QTableWidgetItem("04h"))
        self.choose_BIOS.setItem(10, 1, QTableWidgetItem("05h"))

        # opisy

        self.choose_BIOS.setItem(1, 2, QTableWidgetItem("Wylacza aplikacje; by uruchomic to przerwanie podajemy na AH- 00h"))
        self.choose_BIOS.setItem(2, 2, QTableWidgetItem("Pobiera znak wprowadzony za pomoca konsoli( kod znaku w kodzie ASCII zapisywany jest w AL); by uruchomic to przerwanie podajemy na AH 01h"))
        self.choose_BIOS.setItem(3, 2, QTableWidgetItem("Wyswietla w konsoli znak w kodzie ASCII rejestru DL; by uruchomic to przerwanie podajemy na AH- 02h, DL- kod znaku do wyswietlenia"))
        self.choose_BIOS.setItem(4, 2, QTableWidgetItem("Pobiera ilosc wolnego miejsca na dysku( AX- liczba sektorow w klastrze, BX- liczba wolnych klastrow, CX- liczba bajtow w sektorze, DX- liczba wszystkich klastrow na dysku); by uruchomic przerwanie na AH ustawiamy 36h, na DL- nr dysku(0- domyslny, 1-A, ...)"))

        self.choose_BIOS.setItem(5, 2, QTableWidgetItem("Ustawia kursor w pozycji(x, y); by wywolac to przerwanie nalezy ustawic na AH 02h, x- wartosc DH, y- wartosc DL"))
        self.choose_BIOS.setItem(6, 2, QTableWidgetItem("Pobiera pozycje i rozmiar kursora( DH- kolumna kursora, DL- wiersz, CH- linia poczatku kursora, CL- linia konca); by wywolac to przerwanie nalezy ustawic na AH 03h"))

        self.choose_BIOS.setItem(7, 2, QTableWidgetItem("Sprawdza aktualna godzine w kodzie BCD( CH- godziny, CL- minuty, DH- sekundy); by uruchomic to przerwanie podajemy na AH 02h"))
        self.choose_BIOS.setItem(8, 2, QTableWidgetItem("Ustawia aktualna godzine w kodzie BCD; by uruchomic to przerwanie podajemy na AH 03h, CH- godziny, CL- minuty, DH- sekundy"))
        self.choose_BIOS.setItem(9, 2, QTableWidgetItem("Sprawdza aktualna date w kodzie BCD; zwraca CH- wiek, CL- rok, DH- miesiac, DL- dzien; by uruchomic to przerwanie podajemy na AH 04h"))
        self.choose_BIOS.setItem(10, 2, QTableWidgetItem("Ustawia aktualna date w kodzie BCD; by uruchomic to przerwanie podajemy na AH 04h, CH- wiek, CL- rok, DH- miesiac, DL- dzien"))
        self.choose_BIOS.setColumnWidth(2, 800)
        self.choose_BIOS.setGeometry(100, 100, 1025, 400)

        self.choose_BIOS.show()

    def load_action(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        try:
            fileName, _ = QFileDialog.getOpenFileName(self,"Wybierz plik", "", "Pliki tekstowe (*.txt)", options=options)
            file = open(fileName)
            text = file.read()
            self.program_code.setPlainText(text)
            file.close()
            # print("Pomyslnie wczytano plik")
        except FileNotFoundError:
            print("Blad")

    def save_action(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        try:
            fileName, _ = QFileDialog.getSaveFileName(self, "Wybierz plik", "", "Pliki tekstowe (*.txt)", options=options)
            file = open(fileName, 'w')
            text = self.program_code.toPlainText()
            file.write(text)
            file.close()
            # print("Pomyslnie zapisano plik")
        except FileNotFoundError:
            print("Blad")

    def restore_action(self):
        self.wynik_AH.setText("00000000")
        self.wynik_AL.setText("00000000")
        self.regA.clearReg()
        self.wynik_BH.setText("00000000")
        self.wynik_BL.setText("00000000")
        self.regB.clearReg()
        self.wynik_CH.setText("00000000")
        self.wynik_CL.setText("00000000")
        self.regC.clearReg()
        self.wynik_DH.setText("00000000")
        self.wynik_DL.setText("00000000")
        self.regD.clearReg()
        self.program_counter.setText("000")
        self.max_stack = 15
        self.stack_pointer = 0
        self.stack = []
        self.clearStack()
        # print("Przywrocono")

    def clearStack(self):
        self.stack_pointer_view.setText("15")
        for i in range(self.stack_view.count()):
            self.stack_view.removeItem(0)


    # -------------------------------------
    # STREAM ZEBY MI WYSWIETLALO W KONSOLI TEZ A NIE NORMALNIE

    def onUpdateText(self, text):
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.console.setTextCursor(cursor)
        self.console.ensureCursorVisible()

    def __del__(self):
        sys.stdout = sys.__stdout__

    def initWidgets(self):
        self.label_code = QLabel(self)
        self.label_code.setStyleSheet("background-color: purple; color: white")
        self.label_code.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.label_code.setText("Program")
        self.label_code.setGeometry(QRect(100, 10, 55, 16))

        self.label_code2 = QLabel(self)
        self.label_code2.setStyleSheet("background-color: purple; color: white")
        self.label_code2.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.label_code2.setText("Konsola")
        self.label_code2.setGeometry(QRect(450, 10, 55, 16))

        self.console.setFont(QFont("Verdana", 12))
        self.console.setGeometry(QRect(375, 30, 200, 170))
        self.console.setStyleSheet("background-color: #E0E0E0")
        self.console.moveCursor(QTextCursor.Start)
        self.console.ensureCursorVisible()
        # self.console.setPlainText()
        # self.console.textChanged.connect(self.text_changed_action)

        self.counter = 0
        self.program_code.setFont(QFont("Verdana", 12))
        self.program_code.setGeometry(QRect(20, 30, 220, 190))
        self.program_code.setStyleSheet("background-color: #E0E0E0")
        self.program_code.textChanged.connect(self.text_changed_action)

        self.program_counter = QLabel(self)
        self.program_counter.move(20, 270)
        self.program_counter.setFixedSize(90, 30)
        self.program_counter.setAlignment(Qt.AlignCenter)
        self.program_counter.setFont(QFont("Arial", 16))
        self.program_counter.setText("000")
        self.program_label = QLabel(self)
        self.program_label.move(20, 220)
        self.program_label.setFixedSize(90, 50)
        self.program_label.setAlignment(Qt.AlignCenter)
        self.program_label.setFont(QFont("Arial", 12))
        self.program_label.setText("Counter")

        self.label_reg_AL = self.create_reg_label(550, 220, "AL")
        self.label_reg_AH = self.create_reg_label(350, 220, "AH")
        self.label_reg_BL = self.create_reg_label(550, 300, "BL")
        self.label_reg_BH = self.create_reg_label(350, 300, "BH")
        self.label_reg_CL = self.create_reg_label(550, 380, "CL")
        self.label_reg_CH = self.create_reg_label(350, 380, "CH")
        self.label_reg_DL = self.create_reg_label(550, 460, "DL")
        self.label_reg_DH = self.create_reg_label(350, 460, "DH")

        self.wynik_AH = self.create_reg_view(350, 250, self.regA, True)
        self.wynik_AL = self.create_reg_view(550, 250, self.regA, False)
        self.wynik_BH = self.create_reg_view(350, 330, self.regB, True)
        self.wynik_BL = self.create_reg_view(550, 330, self.regB, False)
        self.wynik_CH = self.create_reg_view(350, 410, self.regC, True)
        self.wynik_CL = self.create_reg_view(550, 410, self.regC, False)
        self.wynik_DH = self.create_reg_view(350, 490, self.regD, True)
        self.wynik_DL = self.create_reg_view(550, 490, self.regD, False)

        self.label_stack_point = QLabel(self)
        self.label_stack_point.move(100, 220)
        self.label_stack_point.setFixedSize(90, 50)
        self.label_stack_point.setAlignment(Qt.AlignCenter)
        self.label_stack_point.setFont(QFont("Arial", 12))
        self.label_stack_point.setText("SP")

        self.stack_pointer_view = QLabel(self)
        self.stack_pointer_view.move(100, 260)
        self.stack_pointer_view.setFixedSize(90, 50)
        self.stack_pointer_view.setAlignment(Qt.AlignCenter)
        self.stack_pointer_view.setFont(QFont("Arial", 16))
        self.stack_pointer_view.setText(str(self.max_stack))

        self.label_stack = self.create_reg_label(20, 315, "STACK")
        self.stack_view = QComboBox(self)
        self.stack_view.move(20, 350)
        self.stack_view.setFixedSize(260, 40)
        self.stack_view.setFont(QFont("Arial", 16))

        self.load_a = QPushButton("Wczytaj zapisany program", self)
        self.load_a.setStyleSheet("background-color: green; color: white;")
        self.load_a.move(730, 160)
        self.load_a.resize(135, 25)
        self.load_a.clicked.connect(self.load_action)
        # self.load_a.setDisabled(True)

        self.save_a = QPushButton("Zapisz do pliku", self)
        self.save_a.setStyleSheet("background-color: green; color: white;")
        self.save_a.move(730, 120)
        self.save_a.resize(135, 25)
        self.save_a.clicked.connect(self.save_action)
        # self.save_a.setDisabled(True)

        self.run_button = QPushButton("Calosciowe wykonanie", self)
        self.run_button.setStyleSheet("background-color: green; color: white;")
        self.run_button.move(730, 80)
        self.run_button.resize(135, 25)
        self.run_button.clicked.connect(self.run_click)
        self.run_button.setDisabled(True)

        self.step_button = QPushButton("Tryb pracy krokowej", self)
        self.step_button.setStyleSheet("background-color: green; color: white;")
        self.step_button.move(730, 40)
        self.step_button.resize(135, 25)
        self.step_button.clicked.connect(self.step_click)
        self.step_button.setDisabled(True)

        self.help_button = QPushButton("Kompiluj", self)
        self.help_button.setStyleSheet("background-color: green; color: white;")
        self.help_button.move(730, 200)
        self.help_button.resize(135, 25)
        self.help_button.clicked.connect(self.compile_action)

        self.edit_button = QPushButton("Instrukcje", self)
        self.edit_button.move(730, 240)
        self.edit_button.setStyleSheet("background-color: green; color: white;")
        self.edit_button.resize(135, 25)
        self.edit_button.clicked.connect(self.edit_click)

        self.help_a = QPushButton("Pomoc", self)
        self.help_a.move(730, 280)
        self.help_a.setStyleSheet("background-color: green; color: white;")
        self.help_a.resize(135, 25)
        self.help_a.clicked.connect(self.help_action)

        self.rest_a = QPushButton("Resetuj", self)
        self.rest_a.move(730, 320)
        self.rest_a.setStyleSheet("background-color: green; color: white;")
        self.rest_a.resize(135, 25)
        self.rest_a.clicked.connect(self.restore_action)


    def changeCode(self, text):
        self.program_code.appendPlainText(text)

    def text_changed_action(self):
        self.run_button.setDisabled(True)
        self.step_button.setDisabled(True)

    def compile_action(self):
        text = self.program_code.toPlainText()
        text = text.split('\n')
        tested = True
        for i in range(len(text)):
            #sprawdz dla kazdego wiersza pattern
            result1 = self.pattern1.match(text[i])
            result2 = self.pattern2.match(text[i])
            result3 = self.pattern3.match(text[i])
            result4 = self.pattern4.match(text[i])
            if not result1 and not result2 and not result3 and not result4:
                print("Blad")
                tested = False
                break
        if tested:
            print("Kompilacja udala sie")
            # QMessageBox.warning(self, ' ',
            #                     "Kompilacja przebiegła poprawnie.", QMessageBox.Yes, QMessageBox.Yes)
            self.run_button.setDisabled(False)
            self.step_button.setDisabled(False)



    def create_reg_view(self, left, top, reg, ind):
        register = QLabel(self)
        if ind:
            register.setText(reg.high)
        else:
            register.setText(reg.low)
        register.setFixedSize(130, 25)
        register.move(left, top)
        register.setAlignment(Qt.AlignCenter)
        register.setFont(QFont("Arial", 16))
        return register

    def create_reg_label(self, left, top, name):
        label_reg = QLabel(self)
        label_reg.setText(name)
        label_reg.move(left, top)
        label_reg.setFont(QFont("Arial", 12))
        return label_reg

    @pyqtSlot()
    def run_click(self):
        text = self.program_code.toPlainText()
        text = text.split('\n')
        for i in range(len(text)):
            commands = text[i].split(" ")
            index = commands[0] # numer instrukcji
            mode = commands[1] # rozkaz
            if "INT" in mode:
                option = 0
            elif mode == "PUSH" or mode == "POP":
                option = 1
                register = commands[2]
            else:
                option = 2
                register = commands[2].split(",") # dane
                if '#' in register[1]:
                     register[1] = register[1][1:]
                     address = True
            while len(index) < 3:
                index = '0' + index
            self.program_counter.setText(index)  # wysiwetl numer instrukcji
            ##################################
            if option == 2:
                op1, c1 = self.findReg(register[0])
                if not address:
                    op2, c2 = self.findReg(register[1])
            elif option == 1:
                op1 = self.findReg(register)
            ##################################
            if mode == 'MOV':
                if not address:
                    number = op2.getReg(c2)
                    op1.mov(number, c1)
                else:
                    number = bin(int(register[1]))[2:]
                    while len(number) < 8:
                        number = '0' + number
                    op1.mov(number, c1)
            if mode == 'ADD':
                if not address:
                    number = op2.getReg(c2)
                    number = int(number, 2)
                    op1.add(number, c1)
                else:
                    number = int(register[1])
                    op1.add(number, c1)
            if mode == 'SUB':
                if not address:
                    number = op2.getReg(c2)
                    number = int(number, 2)
                    op1.sub(number, c1)
                else:
                    number = int(register[1])
                    op1.sub(number, c1)
            if mode == "INT1A":
                if hex(int(self.regA.high, 2)) == "0x2":
                    czas = w32.GetSystemTime()
                    hour = self.convertToBCD(czas[4] + 2)
                    minute = self.convertToBCD(czas[5])
                    second = self.convertToBCD(czas[6])
                    self.regC.high = hour
                    self.regC.low = minute
                    self.regD.high = second
                if hex(int(self.regA.high, 2)) == "0x3":
                    hour = self.convertFromBCD(self.regC.high)-2
                    minute = self.convertFromBCD(self.regC.low)
                    second = self.convertFromBCD(self.regD.high)
                    year = datetime.datetime.now().year
                    month = datetime.datetime.now().month
                    day = datetime.datetime.now().day
                    dayOfWeek = datetime.date.today().weekday()
                    w32.SetSystemTime(year, month, dayOfWeek, day, hour, minute, second, 0)
                if hex(int(self.regA.high, 2)) == "0x4":
                    czas = w32.GetSystemTime()
                    century = self.convertToBCD(int(str(czas[0])[:2]))
                    year = self.convertToBCD(int(str(czas[0])[2:]))
                    month = self.convertToBCD(czas[1])
                    day = self.convertToBCD(czas[3])
                    self.regC.high = century
                    self.regC.low = year
                    self.regD.high = month
                    self.regD.low = day
                if hex(int(self.regA.high, 2)) == "0x5":
                    hour = datetime.datetime.now().time().hour - 2
                    minute = datetime.datetime.now().time().minute
                    second = datetime.datetime.now().time().second
                    year = self.convertFromBCD(self.regC.low)
                    century = 100 * self.convertFromBCD(self.regC.high)
                    month = self.convertFromBCD(self.regD.high)
                    day = self.convertFromBCD(self.regD.low)
                    dayOfWeek = datetime.date.weekday(datetime.date(century+year, month, day))
                    w32.SetSystemTime(century + year, month, dayOfWeek, day, hour, minute, second, 0)
                else:
                    print(" ")

            if mode == "INT10":
                if hex(int(self.regA.high, 2)) == "0x2":
                    x = int(self.regD.high, 2)
                    y = int(self.regD.low, 2)
                    w32.SetCursorPos((x, y))
                else:
                    print(" ")

                if hex(int(self.regA.high, 2)) == "0x3":
                    czas = w32.GetCursorPos()
                    x = self.convertToBCD(int(czas[0]))
                    y = self.convertToBCD(int(czas[1]))
                    self.regD.high = x
                    self.regD.low = y

                else:
                    print(" ")

            if mode == "INT21":
                if hex(int(self.regA.high, 2)) == "0x0":
                    sys.exit(0)
                if hex(int(self.regA.high, 2)) == "0x1":
                    line = sys.stdin.readline()
                    if len(line) > 1:
                        line = line[0]
                    print(line)
                    kod = bin(ord(line))[2:]
                    while len(kod) < 8:
                        kod = '0' + kod
                    self.regA.low = kod
                if hex(int(self.regA.high, 2)) == "0x2":
                    char = self.regD.low
                    self.regA.low = char
                    char = chr(int(char, 2))
                    sys.stdout.write(char)
                if hex(int(self.regA.high, 2)) == "0x36":
                    temp_dict = {1: 'A:', 2: 'B:', 3: 'C:', 4: 'D:', 5: 'E'}
                    temp_dict.setdefault(0, "")
                    ind = int(self.regD.low, 2)
                    test = w32.GetDiskFreeSpace(temp_dict[ind])
                    ra = test[0]
                    rb = test[1]
                    rc = test[2]
                    rd = test[3]
                    if rc >= 256*256:
                        rc = 256*256-1
                    if rd >= 256*256:
                        rd = 256*256-1
                    ra = bin(ra)[2:]
                    while len(ra) < 16:
                        ra = '0' + ra
                    rb = bin(rb)[2:]
                    while len(rb) < 16:
                        rb = '0' + rb
                    rc = bin(rc)[2:]
                    while len(rc) < 16:
                        rc = '0' + rc
                    rd = bin(rd)[2:]
                    while len(rd) < 16:
                        rd = '0' + rd
                    self.regA.high = ra[0:8]
                    self.regA.low = ra[8:16]
                    self.regB.high = rb[0:8]
                    self.regB.low = rb[8:16]
                    self.regC.high = rc[0:8]
                    self.regC.low = rc[8:16]
                    self.regD.high = rd[0:8]
                    self.regD.low = rd[8:16]
                else:
                    print(" ")

            if mode == "PUSH":
                self.stack.insert(0, (op1.getFull(), op1))
                self.updateStack(True)
                self.stack_pointer += 1
            if mode == "POP":
                values = self.stack.pop(0)
                value = values[0]
                reg = values[1]
                reg.high = value[0:8]
                reg.low = value[8:16]
                self.stack_pointer -= 1
                self.updateStack()
            self.stack_pointer_view.setText(str(self.max_stack-self.stack_pointer))
            self.updateReg()
            sleep(1)

    def convertToBCD(self, number):
        text = ""
        for c in str(number):
            temp = bin(int(c))[2:]
            while len(temp) < 4:
                temp = '0' + temp
            text += temp
        while len(text) < 8:
            text = '0' + text
        return text

    def convertFromBCD(self, text):
        number = []
        final = 0
        for i in range(2):
            part = text[0:4]
            part = int(part, 2)
            number.append(part)
            text = text[4:]
        for i in range(len(number)):
            final += 10**i * number.pop(len(number)-1)
        return final

    def updateReg(self):
        self.wynik_AH.setText(self.regA.high)
        self.wynik_AL.setText(self.regA.low)
        self.wynik_BH.setText(self.regB.high)
        self.wynik_BL.setText(self.regB.low)
        self.wynik_CH.setText(self.regC.high)
        self.wynik_CL.setText(self.regC.low)
        self.wynik_DH.setText(self.regD.high)
        self.wynik_DL.setText(self.regD.low)
        QCoreApplication.processEvents()

    def updateStack(self, ind=False):
        if ind:
            self.stack_view.insertItem(0, self.stack[0][1].name + ": " + self.stack[0][0])
            self.stack_view.setCurrentIndex(0)
        else:
            self.stack_view.removeItem(0)
        QCoreApplication.processEvents()

    def findReg(self, text):
        if 'H' in text:
            if 'A' in text:
                return self.regA, True
            elif 'B' in text:
                return self.regB, True
            elif 'C' in text:
                return self.regC, True
            elif 'D' in text:
                return self.regD, True
        elif 'L' in text:
            if 'A' in text:
                return self.regA, False
            elif 'B' in text:
                return self.regB, False
            elif 'C' in text:
                return self.regC, False
            elif 'D' in text:
                return self.regD, False
        elif 'X' in text:
            if 'A' in text:
                return self.regA
            elif 'B' in text:
                return self.regB
            elif 'C' in text:
                return self.regC
            elif 'D' in text:
                return self.regD


    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()
        if self.step:
            if e.key() == Qt.Key_Z:
                self.stop = False


    @pyqtSlot()
    def step_click(self):
        self.step = True
        self.program_code.setDisabled(True)
        QMessageBox.warning(self, ' ',
                            "Nacisnij klawisz 'z' aby zrealizowac nastepny krok.",
                                           QMessageBox.Yes , QMessageBox.Yes)
        text = self.program_code.toPlainText()
        text = text.split('\n')
        for i in range(len(text)):
            self.stop = True
            commands = text[i].split(" ")
            index = commands[0]  # numer instrukcji
            mode = commands[1]  # rozkaz
            if "INT" in mode:
                option = 0
            elif mode == "PUSH" or mode == "POP":
                option = 1
                register = commands[2]
            else:
                option = 2
                register = commands[2].split(",")  # dane
                if '#' in register[1]:
                    register[1] = register[1][1:]
                    address = True
            while len(index) < 3:
                index = '0' + index
            self.program_counter.setText(index)  # wysiwetl numer instrukcji
            ##################################
            if option == 2:
                op1, c1 = self.findReg(register[0])
                if not address:
                    op2, c2 = self.findReg(register[1])
            elif option == 1:
                op1 = self.findReg(register)
            ##################################
            if mode == 'MOV':
                if not address:
                    number = op2.getReg(c2)
                    op1.mov(number, c1)
                else:
                    number = bin(int(register[1]))[2:]
                    while len(number) < 8:
                        number = '0' + number
                    op1.mov(number, c1)
            if mode == 'ADD':
                if not address:
                    number = op2.getReg(c2)
                    number = int(number, 2)
                    op1.add(number, c1)
                else:
                    number = int(register[1])
                    op1.add(number, c1)
            if mode == 'SUB':
                if not address:
                    number = op2.getReg(c2)
                    number = int(number, 2)
                    op1.sub(number, c1)
                else:
                    number = int(register[1])
                    op1.sub(number, c1)
            if mode == "INT1A":
                if hex(int(self.regA.high, 2)) == "0x2":
                    czas = w32.GetSystemTime()
                    hour = self.convertToBCD(czas[4] + 2)
                    minute = self.convertToBCD(czas[5])
                    second = self.convertToBCD(czas[6])
                    self.regC.high = hour
                    self.regC.low = minute
                    self.regD.high = second
                if hex(int(self.regA.high, 2)) == "0x3":
                    hour = self.convertFromBCD(self.regC.high) - 2
                    minute = self.convertFromBCD(self.regC.low)
                    second = self.convertFromBCD(self.regD.high)
                    year = datetime.datetime.now().year
                    month = datetime.datetime.now().month
                    day = datetime.datetime.now().day
                    dayOfWeek = datetime.date.today().weekday()
                    w32.SetSystemTime(year, month, dayOfWeek, day, hour, minute, second, 0)
                if hex(int(self.regA.high, 2)) == "0x4":
                    czas = w32.GetSystemTime()
                    century = self.convertToBCD(int(str(czas[0])[:2]))
                    year = self.convertToBCD(int(str(czas[0])[2:]))
                    month = self.convertToBCD(czas[1])
                    day = self.convertToBCD(czas[3])
                    self.regC.high = century
                    self.regC.low = year
                    self.regD.high = month
                    self.regD.low = day
                if hex(int(self.regA.high, 2)) == "0x5":
                    hour = datetime.datetime.now().time().hour - 2
                    minute = datetime.datetime.now().time().minute
                    second = datetime.datetime.now().time().second
                    year = self.convertFromBCD(self.regC.low)
                    century = 100 * self.convertFromBCD(self.regC.high)
                    month = self.convertFromBCD(self.regD.high)
                    day = self.convertFromBCD(self.regD.low)
                    dayOfWeek = datetime.date.weekday(datetime.date(century + year, month, day))
                    w32.SetSystemTime(century + year, month, dayOfWeek, day, hour, minute, second, 0)
                else:
                    print(" ")
            if mode == "INT10":
                if hex(int(self.regA.high, 2)) == "0x2":
                    x = int(self.regD.high, 2)
                    y = int(self.regD.low, 2)
                    w32.SetCursorPos((x, y))
                else:
                    print(" ")

                if hex(int(self.regA.high, 2)) == "0x3":
                    czas = w32.GetCursorPos()
                    x = self.convertToBCD(int(czas[0]))
                    y = self.convertToBCD(int(czas[1]))
                    self.regD.high = x
                    self.regD.low = y
                else:
                    print(" ")

            if mode == "INT21":
                if hex(int(self.regA.high, 2)) == "0x0":
                    sys.exit(0)
                if hex(int(self.regA.high, 2)) == "0x1":
                    line = sys.stdin.readline()
                    if len(line) > 1:
                        line = line[0]
                    print(line)
                    kod = bin(ord(line))[2:]
                    while len(kod) < 8:
                        kod = '0' + kod
                    self.regA.low = kod

                if hex(int(self.regA.high, 2)) == "0x2":
                    char = self.regD.low
                    self.regA.low = char
                    char = chr(int(char, 2))
                    sys.stdout.write(char)

                if hex(int(self.regA.high, 2)) == "0x36":
                    temp_dict = {1: 'C:', 2: 'D:', 3: 'E:', 4: 'F:'}
                    temp_dict.setdefault(0, "")
                    ind = int(self.regD.low, 2)
                    test = w32.GetDiskFreeSpace(temp_dict[ind])
                    ra = test[0]
                    rb = test[1]
                    rc = test[2]
                    rd = test[3]
                    if rc >= 256 * 256:
                        rc = 256 * 256 - 1
                    if rd >= 256 * 256:
                        rd = 256 * 256 - 1
                    ra = bin(ra)[2:]
                    while len(ra) < 16:
                        ra = '0' + ra
                    rb = bin(rb)[2:]
                    while len(rb) < 16:
                        rb = '0' + rb
                    rc = bin(rc)[2:]
                    while len(rc) < 16:
                        rc = '0' + rc
                    rd = bin(rd)[2:]
                    while len(rd) < 16:
                        rd = '0' + rd
                    self.regA.high = ra[0:8]
                    self.regA.low = ra[8:16]
                    self.regB.high = rb[0:8]
                    self.regB.low = rb[8:16]
                    self.regC.high = rc[0:8]
                    self.regC.low = rc[8:16]
                    self.regD.high = rd[0:8]
                    self.regD.low = rd[8:16]
                else:
                    print(" ")
            if mode == "PUSH":
                self.stack.insert(0, (op1.getFull(), op1))
                self.updateStack(True)
                self.stack_pointer += 1
            if mode == "POP":
                values = self.stack.pop(0)
                value = values[0]
                reg = values[1]
                reg.high = value[0:8]
                reg.low = value[8:16]
                self.stack_pointer -= 1
                self.updateStack()
            self.stack_pointer_view.setText(str(self.max_stack - self.stack_pointer))
            self.updateReg()
            while self.stop:
                QCoreApplication.processEvents()
                sleep(0.01)
        buttonReply = QMessageBox.warning(self, ' ', "Program zakonczony",
                                           QMessageBox.Yes , QMessageBox.Yes)
        if buttonReply == QMessageBox.Yes:
            self.program_code.setDisabled(False)
        self.step = False

    @pyqtSlot()
    def edit_click(self):
        text = self.program_code.toPlainText()
        text = text.split('\n')
        if text[0] == '':
            self.counter = 0
        else:
            self.counter = len(text)*10
        self.okno = PopUpWindow(self.counter, self)
        self.okno.setGeometry(550, 300, 400, 200)
        self.okno.show()


if __name__ == '__main__':
    app = QApplication([])
    ex = Application()
    ex.show()
    sys.exit(app.exec_())