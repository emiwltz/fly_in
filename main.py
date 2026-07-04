import sys


def parser(content: dict[int, str]):
    clean_content = [ligne for ligne in content.values() if not ligne.startswith("#")]


def main():
    path = sys.argv[1]
    print(path)
    contenue = {}
    with open(path, "r") as file:
        for numero, ligne in enumerate(file):
            contenue[numero] = ligne.strip()
    parser(contenue)


if __name__ == "__main__":
    main()
