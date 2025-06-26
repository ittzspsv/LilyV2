from rapidfuzz import process, fuzz

sentence = "raccon 64kg"

for word in sentence.split():
    if word.endswith("kg"):
        try:
            weight = int(word.replace("kg", ""))
            break
        except:
            weight = 1
    else:
        weight = 1

print(weight)