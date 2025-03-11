

def levenshtein_distance_with_indices(str1, str2):
    len_str1 = len(str1)
    len_str2 = len(str2)

    # Create a matrix to store intermediate results
    matrix = [[0] * (len_str2 + 1) for _ in range(len_str1 + 1)]

    # Initialize the matrix
    for i in range(len_str1 + 1):
        matrix[i][0] = i
    for j in range(len_str2 + 1):
        matrix[0][j] = j

    # Initialize a list to store matching indices
    matching_indices = []

    # Fill in the matrix with minimum distances
    for i in range(1, len_str1 + 1):
        for j in range(1, len_str2 + 1):
            cost = 0 if str1[i - 1] == str2[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,      # Deletion
                matrix[i][j - 1] + 1,      # Insertion
                matrix[i - 1][j - 1] + cost  # Substitution
            )

    # Backtrack to find matching indices
    i, j = len_str1, len_str2
    while i > 0 and j > 0:
        if str1[i - 1] == str2[j - 1]:
            matching_indices.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif matrix[i][j] == matrix[i - 1][j] + 1:
            i -= 1  # Deletion
        elif matrix[i][j] == matrix[i][j - 1] + 1:
            j -= 1  # Insertion
        else:
            i -= 1
            j -= 1  # Substitution

    # Reverse the list to get the matching indices in the correct order
    matching_indices.reverse()

    # Return Levenshtein distance and matching indices
    return matrix[len_str1][len_str2], matching_indices


