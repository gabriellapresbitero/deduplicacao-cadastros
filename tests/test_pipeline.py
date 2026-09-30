import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from deduplicacao.__main__ import main
from deduplicacao.avaliacao import avaliar
from deduplicacao.exemplo import gerar_base
from deduplicacao.pipeline import deduplicar
from deduplicacao.registro_mestre import formatar_nome


def cadastro(*linhas):
    colunas = ["id", "nome", "cpf", "email", "telefone", "data_nascimento", "cidade", "atualizado_em"]
    return pd.DataFrame(linhas, columns=colunas)


class TestDeduplicar(unittest.TestCase):
    def test_junta_mesma_pessoa_em_formatos_diferentes(self):
        entrada = cadastro(
            (1, "Maria da Silva", "529.982.247-25", "", "", "", "Recife", "2020-01-01"),
            (2, "MARIA SILVA", "52998224725", "maria@gmail.com", "(81) 8872-0211", "", "recife", "2024-05-01"),
            (3, "João Pereira", "", "joao@gmail.com", "", "", "Olinda", "2023-01-01"),
        )
        resultado = deduplicar(entrada)
        self.assertEqual(resultado.estatisticas["pessoas_unicas"], 2)
        self.assertEqual(resultado.mapa.set_index("id_original")["id_mestre"].to_dict(), {1: 1, 2: 1, 3: 3})

    def test_registro_mestre_combina_os_campos(self):
        entrada = cadastro(
            (1, "Maria Silva", "529.982.247-25", "antigo@gmail.com", "", "10/05/1990", "", "2019-01-01"),
            (2, "MARIA CLARA DA SILVA", "52998224725", "novo@gmail.com", "81988720211", "", "Recife", "2024-01-01"),
        )
        mestre = deduplicar(entrada).unificados.iloc[0]
        self.assertEqual(mestre["nome"], "Maria Clara da Silva")  # o nome mais completo
        self.assertEqual(mestre["email"], "novo@gmail.com")  # o mais recente
        self.assertEqual(mestre["nascimento"], "1990-05-10")  # vazio no recente, vem do antigo
        self.assertEqual(mestre["registros_unidos"], 2)
        self.assertEqual(mestre["ids_originais"], "1,2")

    def test_zona_cinzenta_vai_para_revisao(self):
        entrada = cadastro(
            (1, "Carla Souza", "", "carla@gmail.com", "", "", "", ""),
            (2, "Carla Souza", "", "carla@gmail.com", "", "", "", ""),  # nome + e-mail = 0,70
        )
        resultado = deduplicar(entrada)
        self.assertEqual(resultado.estatisticas["pessoas_unicas"], 2)
        self.assertEqual(len(resultado.revisao), 1)

    def test_valida_entrada(self):
        with self.assertRaisesRegex(ValueError, "id"):
            deduplicar(pd.DataFrame({"nome": ["A"]}))
        with self.assertRaisesRegex(ValueError, "repetidos"):
            deduplicar(pd.DataFrame({"id": [1, 1], "nome": ["A", "B"]}))
        with self.assertRaisesRegex(ValueError, "limiar"):
            deduplicar(cadastro((1, "A", "", "", "", "", "", "")), limiar=0.5, limiar_revisao=0.8)

    def test_funciona_so_com_id_e_nome(self):
        resultado = deduplicar(pd.DataFrame({"id": [1, 2], "nome": ["Ana Lima", "Pedro Costa"]}))
        self.assertEqual(resultado.estatisticas["pessoas_unicas"], 2)

    def test_formatar_nome(self):
        self.assertEqual(formatar_nome("JOSÉ DOS SANTOS"), "José dos Santos")


class TestQualidadeNaBaseDeExemplo(unittest.TestCase):
    """Garante que mudanças no código não pioram o resultado sem ninguém perceber."""

    @classmethod
    def setUpClass(cls):
        cls.base = gerar_base(pessoas=400, semente=1)
        resultado = deduplicar(cls.base.drop(columns="entidade"))
        grupos = cls.base["id"].map(dict(zip(resultado.mapa["id_original"], resultado.mapa["id_mestre"])))
        cls.metricas = avaliar(cls.base["entidade"], grupos)

    def test_precisao_minima(self):
        self.assertGreaterEqual(self.metricas["precisao"], 0.99)

    def test_recall_minimo(self):
        self.assertGreaterEqual(self.metricas["recall"], 0.70)


class TestAvaliacao(unittest.TestCase):
    def test_metricas(self):
        real = pd.Series([1, 1, 1, 2])  # 3 pares reais: (0,1) (0,2) (1,2)
        previsto = pd.Series([1, 1, 3, 2])  # 1 par previsto: (0,1)
        metricas = avaliar(real, previsto)
        self.assertEqual(metricas["precisao"], 1.0)
        self.assertAlmostEqual(metricas["recall"], 1 / 3, places=4)


class TestLinhaDeComando(unittest.TestCase):
    def test_gera_exemplo_e_deduplica(self):
        pasta = Path(tempfile.mkdtemp())
        with contextlib.redirect_stdout(io.StringIO()) as saida:
            self.assertEqual(main(["--gerar-exemplo", str(pasta / "base.csv"), "--pessoas", "50"]), 0)
            self.assertEqual(main([str(pasta / "base.csv"), "--saida", str(pasta / "saida")]), 0)
        self.assertIn("Precisão", saida.getvalue())
        for nome in ["clientes_unificados.csv", "mapa_ids.csv", "pares_para_revisao.csv",
                     "qualidade_campos.csv", "relatorio.md"]:
            with self.subTest(arquivo=nome):
                self.assertTrue((pasta / "saida" / nome).exists())

    def test_aceita_csv_com_ponto_e_virgula(self):
        pasta = Path(tempfile.mkdtemp())
        (pasta / "base.csv").write_text("id;nome;email\n1;Ana Lima;ana@x.com\n2;ANA LIMA;ana@x.com\n", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([str(pasta / "base.csv"), "--saida", str(pasta / "saida")]), 0)

    def test_sem_arquivo_retorna_erro(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([]), 1)


if __name__ == "__main__":
    unittest.main()
