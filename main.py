import sys


def parser(content: dict[int, str]):
    clean_content = {
        numero: ligne for numero, ligne in content.items() if not ligne.startswith("#")
    }
    first = clean_content[1].split()
    drone_nb = first[1]
    hubs = {
        numero: ligne for numero, ligne in clean_content.items() if ligne.startswith("hub")
    }
    connections = {
        numero: ligne
        for numero, ligne in clean_content.items()
        if ligne.startswith("connection")
    }
    start = {
        numero: ligne
        for numero, ligne in clean_content.items()
        if ligne.startswith("start_hub:")
    }
    end = {
        numero: ligne
        for numero, ligne in clean_content.items()
        if ligne.startswith("end_hub:")
    }
    return (drone_nb, start, end, hubs, connections)


def parsing_hub(hub):
    pass

def parsing_connection(connection):
    pass

def main():
    path = sys.argv[1]
    contenue = {}
    with open(path, "r") as file:
        for numero, ligne in enumerate(file):
            contenue[numero] = ligne.strip()
    drone_nb, start, end, hubs, connections = parser(contenue)

    print("DEBUG_PARSER")
    print()

    print(f"nb_drone: {drone_nb}")
    print(f"start: {start}")
    print(f"end: {end}")
    # print(f"hubs: {hubs}")
    # print(f"connections: {connections}")


if __name__ == "__main__":
    main()
