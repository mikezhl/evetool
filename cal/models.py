from django.db import models

class Remain(models.Model):
    token = models.IntegerField(blank=True, null=True)
    item_id = models.IntegerField(blank=True, null=True)
    quantity = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'remain'


class Sdecate(models.Model):
    groupid = models.IntegerField(db_column='groupID', primary_key=True)  # Field name made lowercase.
    categoryid = models.IntegerField(db_column='categoryID', blank=True, null=True)  # Field name made lowercase.
    groupname = models.CharField(db_column='groupName', max_length=100, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'sdecate'


class Sdeconvert(models.Model):
    typeid = models.IntegerField(db_column='typeID', blank=True, null=True)  # Field name made lowercase.
    activityid = models.IntegerField(db_column='activityID', blank=True, null=True)  # Field name made lowercase.
    producttypeid = models.IntegerField(db_column='productTypeID', blank=True, null=True)  # Field name made lowercase.
    quantity = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sdeconvert'


class Sdematerial(models.Model):
    typeid = models.IntegerField(blank=True, null=True)
    activityid = models.IntegerField(blank=True, null=True)
    materialtypeid = models.IntegerField(blank=True, null=True)
    quantity = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sdematerial'


class Sdenames(models.Model):
    typeid = models.IntegerField(primary_key=True)
    groupid = models.IntegerField(blank=True, null=True)
    typename = models.CharField(max_length=100, blank=True, null=True)
    raceid = models.IntegerField(blank=True, null=True)
    baseprice = models.DecimalField(max_digits=19, decimal_places=4, blank=True, null=True)
    marketgroupid = models.IntegerField(blank=True, null=True)
    adjprice = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sdenames'


class Sdeore(models.Model):
    typeid = models.IntegerField(db_column='typeID', primary_key=True)  # Field name made lowercase.
    materialtypeid = models.IntegerField(db_column='materialTypeID')  # Field name made lowercase.
    quantity = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'sdeore'
        unique_together = (('typeid', 'materialtypeid'),)


class Sderuns(models.Model):
    typeid = models.IntegerField(primary_key=True)
    maxproductionlimit = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sderuns'


class User(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    token = models.PositiveIntegerField(blank=True, null=True)
    system = models.TextField(blank=True, null=True)
    tax_reaction = models.FloatField(blank=True, null=True)
    tax_component = models.FloatField(blank=True, null=True)
    tax_standard = models.FloatField(blank=True, null=True)
    tax_cap = models.FloatField(blank=True, null=True)
    tax_super = models.FloatField(blank=True, null=True)
    index_reaction = models.FloatField(blank=True, null=True)
    index_manufacturing = models.FloatField(blank=True, null=True)
    me_reaction = models.FloatField(blank=True, null=True)
    me_component = models.FloatField(blank=True, null=True)
    me_ship_m = models.FloatField(blank=True, null=True)
    me_ship_s = models.FloatField(blank=True, null=True)
    me_others = models.FloatField(blank=True, null=True)
    me_cap_comp = models.FloatField(blank=True, null=True)
    me_cap = models.FloatField(blank=True, null=True)
    min_reaction = models.IntegerField(blank=True, null=True)
    update_price = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user'
