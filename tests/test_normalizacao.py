import unittest

from deduplicacao import normalizacao as norm


class TestNome(unittest.TestCase):
    def test_remove_acentos_particulas_e_espacos(self):
        self.assertEqual(norm.normalizar_nome("  José  da Silva "), "JOSE SILVA")

    def test_remove_simbolos_e_numeros(self):
        self.assertEqual(norm.normalizar_nome("Ana-Maria O'Neil 2"), "ANA MARIA O NEIL")

    def test_vazio(self):
        self.assertEqual(norm.normalizar_nome(None), "")
        self.assertEqual(norm.normalizar_nome(""), "")


class TestCpf(unittest.TestCase):
    def test_aceita_com_ou_sem_mascara(self):
        self.assertEqual(norm.normalizar_cpf("529.982.247-25"), "52998224725")
        self.assertEqual(norm.normalizar_cpf("52998224725"), "52998224725")

    def test_recupera_zero_a_esquerda_perdido_na_planilha(self):
        # 076.647.542-59 é válido; o Excel costuma salvar como 7664754259
        self.assertEqual(norm.normalizar_cpf("7664754259"), "07664754259")

    def test_invalido_vira_vazio(self):
        for cpf in ["529.982.247-24", "111.111.111-11", "123", "123456789012", ""]:
            with self.subTest(cpf=cpf):
                self.assertEqual(norm.normalizar_cpf(cpf), "")


class TestEmail(unittest.TestCase):
    def test_minusculas_e_espacos(self):
        self.assertEqual(norm.normalizar_email("  Maria.Silva@Gmail.COM "), "maria.silva@gmail.com")

    def test_invalidos(self):
        for email in ["maria.silvagmail.com", "maria@", "maria@gmail", "", None]:
            with self.subTest(email=email):
                self.assertEqual(norm.normalizar_email(email), "")


class TestTelefone(unittest.TestCase):
    def test_formatos_do_mesmo_celular(self):
        formatos = ["(81) 98872-0211", "+55 81 98872-0211", "081 98872-0211", "81988720211",
                    "(81) 8872-0211"]  # o último é o formato antigo, sem o 9
        for telefone in formatos:
            with self.subTest(telefone=telefone):
                self.assertEqual(norm.normalizar_telefone(telefone), "81988720211")

    def test_telefone_fixo_nao_ganha_nove(self):
        self.assertEqual(norm.normalizar_telefone("(81) 3222-1234"), "8132221234")

    def test_invalidos(self):
        for telefone in ["12345", "", None, "(00) 3222-1234"]:
            with self.subTest(telefone=telefone):
                self.assertEqual(norm.normalizar_telefone(telefone), "")


class TestData(unittest.TestCase):
    def test_formatos(self):
        for valor in ["31/12/1990", "1990-12-31", "31-12-1990"]:
            with self.subTest(valor=valor):
                self.assertEqual(norm.normalizar_data(valor), "1990-12-31")

    def test_datas_impossiveis(self):
        for valor in ["31/02/1990", "01/01/1800", "01/01/2999", "ontem", ""]:
            with self.subTest(valor=valor):
                self.assertEqual(norm.normalizar_data(valor), "")


if __name__ == "__main__":
    unittest.main()
