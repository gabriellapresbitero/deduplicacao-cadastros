import unittest

from deduplicacao.agrupamento import UnionFind, agrupar
from deduplicacao.blocagem import TAMANHO_MAXIMO_BLOCO, gerar_pares
from deduplicacao.similaridade import pontuar_par, similaridade_nomes


def registro(nome="MARIA SILVA", cpf="", email="", telefone="", nascimento=""):
    return {"nome_norm": nome, "cpf": cpf, "email": email, "telefone": telefone, "nascimento": nascimento}


class TestSimilaridadeNomes(unittest.TestCase):
    def test_iguais(self):
        self.assertEqual(similaridade_nomes("MARIA SILVA", "MARIA SILVA"), 1.0)

    def test_erro_de_digitacao(self):
        self.assertGreater(similaridade_nomes("MARIA SILVA", "MAIRA SILVA"), 0.85)

    def test_nome_do_meio_faltando(self):
        self.assertGreaterEqual(similaridade_nomes("MARIA SILVA", "MARIA CLARA SILVA"), 0.9)

    def test_ordem_trocada(self):
        self.assertGreater(similaridade_nomes("SILVA MARIA", "MARIA SILVA"), 0.95)

    def test_nomes_diferentes(self):
        self.assertLess(similaridade_nomes("MARIA SILVA", "JOAO PEREIRA"), 0.5)

    def test_vazio(self):
        self.assertEqual(similaridade_nomes("", "MARIA"), 0.0)


class TestPontuarPar(unittest.TestCase):
    def test_mesmo_cpf_decide(self):
        self.assertEqual(pontuar_par(registro(cpf="1"), registro(nome="OUTRO NOME", cpf="1"))[0], 1.0)

    def test_cpfs_diferentes_nunca_juntam(self):
        pontos, motivo = pontuar_par(registro(cpf="1", email="a@b.com"), registro(cpf="2", email="a@b.com"))
        self.assertEqual(pontos, 0.0)
        self.assertIn("diferentes", motivo)

    def test_nome_email_e_telefone(self):
        pontos, motivo = pontuar_par(registro(email="a@b.com", telefone="81999999999"),
                                     registro(email="a@b.com", telefone="81999999999"))
        self.assertAlmostEqual(pontos, 0.9)
        self.assertIn("mesmo e-mail", motivo)

    def test_so_o_nome_nao_basta(self):
        # homônimos: mesmo nome não quer dizer mesma pessoa
        self.assertEqual(pontuar_par(registro(), registro())[0], 0.5)

    def test_pai_e_filho_com_mesmo_nome_e_telefone(self):
        pai = registro(telefone="8132221234", nascimento="1960-01-01")
        filho = registro(telefone="8132221234", nascimento="1990-05-05")
        self.assertLess(pontuar_par(pai, filho)[0], 0.6)


class TestBlocagem(unittest.TestCase):
    def test_so_compara_quem_compartilha_alguma_chave(self):
        registros = [
            registro("ANA LIMA", email="ana@x.com"),
            registro("ANA L", email="ana@x.com"),
            registro("PEDRO COSTA", telefone="81999999999"),
        ]
        self.assertEqual(gerar_pares(registros), {(0, 1)})

    def test_bloco_gigante_e_ignorado(self):
        # Um telefone de empresa usado por muita gente não deve gerar milhares de pares.
        registros = [registro(f"PESSOA{i} SOBRENOME{i}", telefone="8130000000")
                     for i in range(TAMANHO_MAXIMO_BLOCO + 1)]
        self.assertEqual(gerar_pares(registros), set())


class TestAgrupamento(unittest.TestCase):
    def test_transitividade(self):
        # 0-1 e 1-2 são pares, então 0, 1 e 2 são o mesmo grupo
        self.assertEqual(agrupar(["", "", "", ""], [(0, 1), (1, 2)]), [0, 0, 0, 3])

    def test_nao_junta_cpfs_diferentes_por_uma_ponte(self):
        # 1 não tem CPF e parece com 0 e com 2, mas 0 e 2 têm CPFs diferentes
        grupos = agrupar(["111", "", "222"], [(0, 1), (1, 2)])
        self.assertEqual(grupos[0], grupos[1])
        self.assertNotEqual(grupos[1], grupos[2])

    def test_union_find_informa_uniao_recusada(self):
        uf = UnionFind(["111", "222"])
        self.assertFalse(uf.unir(0, 1))


if __name__ == "__main__":
    unittest.main()
