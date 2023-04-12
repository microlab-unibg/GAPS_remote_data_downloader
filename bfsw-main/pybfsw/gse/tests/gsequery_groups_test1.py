from pybfsw.gse.gsequery import GSEQuery

q = GSEQuery(project='gaps')
parameters = ['@vbus_pdu0ch1','pdu_hkp:counter','@ibus_pdu0ch5']
pg = q.make_parameter_groups(parameters)

res = q.get_latest_value_groups(pg)

print ("res: ", res)
print("res.items(): ", res.items())

print (res["@vbus_pdu0ch1"][1])

for r in res.items():
    print(r)
    
for r in res.items():
    print(r[0].split("pdu")[1][0])
    print(r[1][1])

print (res.items())
