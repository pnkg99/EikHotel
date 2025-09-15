from PyQt5.QtWidgets import QWidget, QHBoxLayout
from PyQt5.QtCore import Qt
import os

from button import IconTextButton
from lang import LANG
from msgmodal import CustomModal

def on_help():
    modal = CustomModal(modal_type="help")
    #modal.
    modal.show()

class BottomBar(QWidget):
    def __init__(self, parent=None, show_back=False, on_back=None, show_help=True, variant=1):
        super().__init__(parent)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)  
        self.layout.setSpacing(20)
        # Posle kreiranja layout-a
        self.layout.setAlignment(Qt.AlignVCenter)  # Vertikalno centriranje dugmića
        
        back_icon = ""
        back_title = ""
        if variant == 1:
            back_icon = os.path.join("public", "icons", "close_small.png")
            back_title = LANG["CANCEL"]
        elif variant == 2:
            back_icon = os.path.join("public", "icons", "get_back.png")
            back_title = LANG["BACK"]


        # Ako se prikazuju oba dugmeta (back i help)
        if show_back and show_help:
            # Nazad dugme levo
            back_button = IconTextButton(
                back_title,
                back_icon,
                click_callback=on_back,
                reverse=True
            )
            self.layout.addWidget(back_button)  # Bez alignment parametra

            self.layout.addStretch()  # Gurni dugmiće na krajnje pozicije

            # Help dugme desno
            help_button = IconTextButton(
                LANG["HELP"],
                os.path.join("public", "icons", "contact_support.png"),
                click_callback=on_help
            )
            self.layout.addWidget(help_button)  # Bez alignment parametra
        
        # Ako se prikazuje samo back dugme
        elif show_back and not show_help:
            # Nazad dugme levo
            back_button = IconTextButton(
                back_title,
                back_icon,
                click_callback=on_back,
                reverse=True
            )
            self.layout.addWidget(back_button)
            self.layout.addStretch()
        
        # Ako se prikazuje samo help dugme
        elif not show_back and show_help:
            # Samo Help dugme centrirano
            self.layout.addStretch()
            help_button = IconTextButton(
                LANG["HELP"],
                os.path.join("public", "icons", "contact_support.png"),
                click_callback=on_help
            )  
            self.layout.addWidget(help_button)
            self.layout.addStretch()
        
        # Ako se ne prikazuje nijedan dugme (prazan bar)
        else:
            self.layout.addStretch()